
import os
import re
import pickle
import threading
import urllib.parse
import urllib.request
import webbrowser

import numpy as np
import pandas as pd
import customtkinter as ctk
from scipy.sparse import load_npz

try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False

try:
    import vlc
    VLC_AVAILABLE = True
except Exception:
    VLC_AVAILABLE = False

ctk.set_appearance_mode("light")


C = {
    "bg":          "#ECE7DD", 
    "surface":     "#F6F2E9",  
    "surface_alt": "#EFE9DC",   
    "shadow":      "#CFC7B6",   
    "border":      "#DED5C1",
    "text":        "#2E2A22",
    "text_muted":  "#867C6B",
    "accent":      "#C1602F",  
    "accent_dark": "#A24E26",
    "accent_soft": "#ECD9C8",
    "good":        "#3F7355",
    "bad":         "#B23A33",
}

FONT_FAMILY = "Helvetica"


def font(size, weight="normal"):
    return (FONT_FAMILY, size, weight)

class NeuPanel(ctk.CTkFrame):
    def __init__(self, parent, height, radius=18, depth=4, surface_color=None, **surface_kwargs):
        super().__init__(parent, fg_color="transparent", height=height + depth)
        self._depth = depth

        self.shadow = ctk.CTkFrame(self, fg_color=C["shadow"], corner_radius=radius)
        self.surface = ctk.CTkFrame(
            self,
            fg_color=surface_color or C["surface"],
            corner_radius=radius,
            border_width=1,
            border_color=C["border"],
            **surface_kwargs,
        )
        self.shadow.place(x=depth, y=depth)
        self.surface.place(x=0, y=0)
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        w = max(event.width - self._depth, 1)
        h = max(event.height - self._depth, 1)
        self.shadow.configure(width=w, height=h)
        self.surface.configure(width=w, height=h)
class TrackResolver:
    def __init__(self):
        self._watch_cache = {}
        self._stream_cache = {}

    def resolve_watch_url(self, query):
        if query in self._watch_cache:
            return self._watch_cache[query]

        url = self._search_with_ytdlp(query) if YTDLP_AVAILABLE else None
        if url is None:
            url = self._search_with_regex(query)

        if url:
            self._watch_cache[query] = url
        return url

    def resolve_audio_stream(self, query):
        """Direct, playable audio URL for local in-app playback. Requires yt-dlp."""
        if not YTDLP_AVAILABLE:
            return None
        if query in self._stream_cache:
            return self._stream_cache[query]

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "format": "bestaudio/best",
            "default_search": "ytsearch1",
            "noplaylist": True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=False)
                entry = info["entries"][0] if "entries" in info else info
                stream_url = entry.get("url")
                if stream_url:
                    self._stream_cache[query] = stream_url
                return stream_url
        except Exception as e:
            print(f"yt-dlp stream extraction failed: {e}")
            return None

    def _search_with_ytdlp(self, query):
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "default_search": "ytsearch1",
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=False)
                entry = info["entries"][0] if "entries" in info else info
                video_id = entry.get("id")
                if video_id:
                    return f"https://www.youtube.com/watch?v={video_id}"
        except Exception as e:
            print(f"yt-dlp search failed, falling back to regex scrape: {e}")
        return None

    def _search_with_regex(self, query):
        """Original scraping approach — kept as a dependency-free fallback."""
        try:
            query_encoded = urllib.parse.quote(query)
            url = f"https://www.youtube.com/results?search_query={query_encoded}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            html = urllib.request.urlopen(req, timeout=8).read().decode(errors="ignore")
            video_ids = re.findall(r"watch\?v=(\S{11})", html)
            if video_ids:
                return f"https://www.youtube.com/watch?v={video_ids[0]}"
        except Exception as e:
            print(f"Regex scrape failed: {e}")
        return None


class AudioPlayer:
    def __init__(self):
        self.enabled = False
        self.instance = None
        self.player = None
        self.current_title = None

        if VLC_AVAILABLE:
            try:
                self.instance = vlc.Instance("--quiet")
                self.player = self.instance.media_player_new()
                self.enabled = True
            except Exception as e:
                print(f"VLC native library not found — local playback disabled ({e}). "
                      f"Install VLC itself (e.g. 'sudo apt install vlc') to enable it.")

    def play_url(self, url, title=None):
        if not self.enabled:
            return False
        media = self.instance.media_new(url)
        self.player.set_media(media)
        self.player.play()
        self.current_title = title
        return True

    def toggle_pause(self):
        if self.enabled and self.player.get_media():
            self.player.pause()

    def stop(self):
        if self.enabled:
            self.player.stop()
            self.current_title = None

    def is_playing(self):
        return bool(self.enabled and self.player.is_playing() == 1)

    def position(self):
        """Returns (current_seconds, total_seconds). total may be 0 briefly after load."""
        if not self.enabled:
            return 0, 0
        length = max(self.player.get_length(), 0) / 1000
        current = max(self.player.get_time(), 0) / 1000
        return current, length

    def release(self):
        if self.enabled:
            self.player.stop()
            self.player.release()
            self.instance.release()


class MusicDiscoveryApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Music Discovery Studio")
        self.geometry("960x720")
        self.minsize(820, 600)
        self.configure(fg_color=C["bg"])

        self.resolver = TrackResolver()
        self.player = AudioPlayer()
        self._progress_job = None

        self.load_assets()
        self._build_ui()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def load_assets(self):
        """Loads model and matrix data safely from disk (unchanged from original)."""
        try:
            with open("Main_data/lightfm_model.pkl", "rb") as f:
                data = pickle.load(f)
            self.model = data["model"]
            self.users = data["users"]
            self.items = data["items"]

            self.train_matrix = load_npz("Main_data/train_matrix.npz").tocsr()
            self.songs = pd.read_csv("Main_data/songs.csv")
        except Exception as e:
            print(f"Error loading system assets: {e}")
            self.model = None


    def _build_ui(self):
        header = NeuPanel(self, height=148)
        header.pack(fill="x", padx=28, pady=(24, 10))

        ctk.CTkLabel(
            header.surface, text="🎧  MUSIC DISCOVERY STUDIO",
            font=font(22, "bold"), text_color=C["text"],
        ).pack(anchor="w", padx=26, pady=(20, 2))

        ctk.CTkLabel(
            header.surface, text="Personalized picks from your listening history",
            font=font(12), text_color=C["text_muted"],
        ).pack(anchor="w", padx=26, pady=(0, 14))

        control_row = ctk.CTkFrame(header.surface, fg_color="transparent")
        control_row.pack(fill="x", padx=26, pady=(0, 18))

        self.input_entry = ctk.CTkEntry(
            control_row, placeholder_text="Enter Playlist ID (e.g., 5002)...",
            height=46, fg_color=C["surface_alt"], text_color=C["text"],
            placeholder_text_color=C["text_muted"], border_width=1,
            border_color=C["border"], corner_radius=14, font=font(14),
        )
        self.input_entry.pack(side="left", expand=True, fill="x", padx=(0, 14))
        self.input_entry.bind("<Return>", lambda e: self.start_recommendation_thread())

        self.submit_btn = ctk.CTkButton(
            control_row, text="Generate Recs", command=self.start_recommendation_thread,
            height=46, width=160, fg_color=C["accent"], hover_color=C["accent_dark"],
            text_color="#FFFFFF", corner_radius=14, font=font(14, "bold"), border_width=0,
        )
        self.submit_btn.pack(side="right")
        self.status_panel = NeuPanel(self, height=42, depth=3, radius=12)
        self.status_panel.pack(fill="x", padx=28, pady=(0, 10))
        self.status_label = ctk.CTkLabel(
            self.status_panel.surface,
            text="Ready — enter a playlist ID to begin."
            if self.model is not None else
            "⚠ Couldn't load Main_data assets — check console for details.",
            font=font(12, "bold"), text_color=C["text_muted"], anchor="w",
        )
        self.status_label.pack(fill="x", padx=18, pady=8)

        self.now_playing_panel = NeuPanel(self, height=92, depth=4)
        self.now_playing_panel.pack(side="bottom", fill="x", padx=28, pady=(10, 24))
        self._build_now_playing_bar(self.now_playing_panel.surface)

        ctk.CTkLabel(
            self, text="YOUR PERSONALIZED DISCOVERIES",
            font=font(12, "bold"), text_color=C["text_muted"],
        ).pack(anchor="w", padx=34, pady=(2, 0))

        self.scroll_container = ctk.CTkScrollableFrame(
            self, fg_color=C["surface_alt"], corner_radius=18,
            border_width=1, border_color=C["border"],
        )
        self.scroll_container.pack(fill="both", expand=True, padx=28, pady=(6, 10))

    def _build_now_playing_bar(self, parent):
        parent.grid_columnconfigure(1, weight=1)

        default_text = "Nothing playing yet" if self.player.enabled else \
            "Local playback unavailable — install yt-dlp & VLC to enable it"
        self.np_title = ctk.CTkLabel(
            parent, text=default_text, font=font(13, "bold"),
            text_color=C["text"], anchor="w",
        )
        self.np_title.grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(14, 2))

        self.play_pause_btn = ctk.CTkButton(
            parent, text="▶", width=42, height=42, corner_radius=21,
            fg_color=C["accent"], hover_color=C["accent_dark"], text_color="#FFFFFF",
            font=font(16, "bold"), command=self.toggle_playback, state="disabled",
        )
        self.play_pause_btn.grid(row=1, column=0, padx=(20, 10), pady=(0, 14))

        self.progress_slider = ctk.CTkSlider(
            parent, from_=0, to=100, height=14, progress_color=C["accent"],
            button_color=C["accent_dark"], fg_color=C["border"], state="disabled",
        )
        self.progress_slider.set(0)
        self.progress_slider.grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 14))

        self.time_label = ctk.CTkLabel(
            parent, text="0:00 / 0:00", font=font(11), text_color=C["text_muted"],
        )
        self.time_label.grid(row=1, column=2, padx=(0, 20), pady=(0, 14))

    def set_status(self, text, kind="muted"):
        color = {
            "muted": C["text_muted"], "accent": C["accent"],
            "bad": C["bad"], "good": C["good"],
        }.get(kind, C["text_muted"])
        self.after(0, lambda: self.status_label.configure(text=text, text_color=color))

    def start_recommendation_thread(self):
        threading.Thread(target=self.generate_recommendations, daemon=True).start()

    def generate_recommendations(self):
        if self.model is None:
            self.set_status("⚠ Model assets failed to load — check Main_data/.", "bad")
            return

        raw_id = self.input_entry.get().strip()
        if not raw_id:
            self.set_status("Enter a playlist ID first.", "bad")
            return

        self.set_status("🔄 Generating recommendations…", "accent")

        try:
            playlist_id = int(raw_id)
            user_idx = self.users.index(playlist_id)
        except (ValueError, IndexError):
            self.after(0, self._render_error, "Invalid Playlist ID or User Not Found.")
            return

        scores = self.model.predict(user_idx, np.arange(len(self.items)))
        known_items = self.train_matrix[user_idx].indices
        scores[known_items] = -np.inf 

        top_indices = np.argsort(-scores)[:20]
        recommended_uris = [self.items[idx] for idx in top_indices]
        scores_dict = {self.items[idx]: scores[idx] for idx in top_indices}

        recommended_uris_clean = [uri.replace("spotify:track:", "") for uri in recommended_uris]

        recs = self.songs[self.songs["track_uri"].isin(recommended_uris_clean)].copy()
        recs = recs.drop_duplicates(subset=["track_uri"])

        recs["full_uri"] = recs["track_uri"].apply(lambda x: f"spotify:track:{x}" if not x.startswith("spotify:") else x)
        recs["score"] = recs["full_uri"].map(scores_dict)
        recs = recs.sort_values(by="score", ascending=False)

        if len(recs) > 0:
            lo, hi = recs["score"].min(), recs["score"].max()
            spread = (hi - lo) or 1.0
            recs["match_pct"] = ((recs["score"] - lo) / spread * 35 + 65).round().astype(int)
        else:
            recs["match_pct"] = []

        self.after(0, self._render_results, recs)

    def _render_error(self, message):
        self.clear_scroll_container()
        ctk.CTkLabel(
            self.scroll_container, text=f"❌ {message}",
            text_color=C["bad"], font=font(13, "bold"),
        ).pack(pady=24)
        self.set_status(message, "bad")

    def _render_results(self, recs):
        self.clear_scroll_container()
        if len(recs) == 0:
            ctk.CTkLabel(
                self.scroll_container, text="No recommendations found.",
                text_color=C["text_muted"],
            ).pack(pady=24)
            self.set_status("No recommendations found.", "bad")
            return

        for _, row in recs.iterrows():
            self._add_result_row(row["track_name"], row["artist_name"], row["album_name"], int(row["match_pct"]))

        self.set_status(f"✅ Found {len(recs)} recommendations.", "good")

    def clear_scroll_container(self):
        for widget in self.scroll_container.winfo_children():
            widget.destroy()

    def _add_result_row(self, track_name, artist_name, album_name, match_pct):
        row = NeuPanel(self.scroll_container, height=78, radius=14, depth=3, surface_color=C["surface"])
        row.pack(fill="x", padx=10, pady=6)

        surface = row.surface
        surface.grid_columnconfigure(0, weight=1)

        text_frame = ctk.CTkFrame(surface, fg_color="transparent")
        text_frame.grid(row=0, column=0, sticky="ew", padx=(18, 10), pady=10)

        ctk.CTkLabel(
            text_frame, text=f"{track_name} — {artist_name}",
            font=font(14, "bold"), text_color=C["text"], anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            text_frame, text=f"Album: {album_name}",
            font=font(11), text_color=C["text_muted"], anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            surface, text=f"{match_pct}% match", font=font(11, "bold"),
            text_color=C["accent"], fg_color=C["accent_soft"],
            corner_radius=10, width=80, height=24,
        ).grid(row=0, column=1, padx=8, pady=10)

        search_query = f"{track_name} {artist_name} official audio"
        display_title = f"{track_name} — {artist_name}"

        ctk.CTkButton(
            surface, text="▶ Play", width=78, height=34, corner_radius=10,
            fg_color=C["accent"] if self.player.enabled else C["border"],
            hover_color=C["accent_dark"],
            text_color="#FFFFFF" if self.player.enabled else C["text_muted"],
            font=font(12, "bold"), state="normal" if self.player.enabled else "disabled",
            command=lambda q=search_query, t=display_title: self.start_play_thread(q, t),
        ).grid(row=0, column=2, padx=(4, 6), pady=10)

        ctk.CTkButton(
            surface, text="YouTube ↗", width=92, height=34, corner_radius=10,
            fg_color="transparent", hover_color=C["surface_alt"], border_width=1,
            border_color=C["border"], text_color=C["text_muted"], font=font(12, "bold"),
            command=lambda q=search_query: self.start_open_thread(q),
        ).grid(row=0, column=3, padx=(0, 16), pady=10)

    def start_open_thread(self, query):
        threading.Thread(target=self._open_in_browser, args=(query,), daemon=True).start()

    def _open_in_browser(self, query):
        self.set_status(f"🔎 Looking up “{query}”…", "accent")
        url = self.resolver.resolve_watch_url(query)
        if url:
            self.set_status("🌐 Opening in your browser…", "good")
            webbrowser.open(url)
        else:
            self.set_status("Could not find a matching YouTube link.", "bad")

    def start_play_thread(self, query, title):
        threading.Thread(target=self._play_locally, args=(query, title), daemon=True).start()

    def _play_locally(self, query, title):
        if not self.player.enabled:
            self.set_status("Local playback needs yt-dlp + VLC installed.", "bad")
            return
        self.set_status(f"🔎 Finding audio for “{title}”…", "accent")
        stream_url = self.resolver.resolve_audio_stream(query)
        if not stream_url:
            self.set_status("Couldn't resolve a playable audio stream.", "bad")
            return
        self.player.play_url(stream_url, title=title)
        self.set_status(f"▶ Playing: {title}", "good")
        self.after(0, self._on_playback_started, title)

    def _on_playback_started(self, title):
        self.np_title.configure(text=title)
        self.play_pause_btn.configure(state="normal", text="⏸")
        self.progress_slider.configure(state="normal")
        self._poll_progress()

    def toggle_playback(self):
        if not self.player.enabled:
            return
        self.player.toggle_pause()
        playing = self.player.is_playing()
        self.play_pause_btn.configure(text="⏸" if playing else "▶")

    def _poll_progress(self):
        if self.player.enabled and self.player.current_title:
            current, total = self.player.position()
            if total > 0:
                self.progress_slider.set(min(current / total * 100, 100))
            self.time_label.configure(text=f"{self._fmt(current)} / {self._fmt(total)}")
        self._progress_job = self.after(500, self._poll_progress)

    @staticmethod
    def _fmt(seconds):
        seconds = max(int(seconds), 0)
        return f"{seconds // 60}:{seconds % 60:02d}"

    def _on_close(self):
        if self._progress_job:
            self.after_cancel(self._progress_job)
        self.player.release()
        self.destroy()


if __name__ == "__main__":
    app = MusicDiscoveryApp()
    app.mainloop()