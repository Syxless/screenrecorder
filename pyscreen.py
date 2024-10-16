import cv2
import numpy as np
import pyautogui
import pyaudio
import threading
import tkinter as tk
from tkinter import ttk
from screeninfo import get_monitors
import time
import wave
import os

class ScreenRecorderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OBS-like Screen Recorder")
        self.root.geometry("600x400")
        
        self.recording = False
        self.paused = False
        self.screen_size = None
        self.selected_monitor = 0
        self.monitor_list = self.get_monitors()

        # GUI Components
        self.create_widgets()

        # Initialize video and audio settings
        self.out = None
        self.audio_stream = None
        self.audio_frames = []
        self.video_thread = None
        self.audio_thread = None

    def create_widgets(self):
        """ Create buttons and drop-down for monitor selection """
        self.record_btn = ttk.Button(self.root, text="Start Recording", command=self.start_recording)
        self.record_btn.pack(pady=10)

        self.pause_btn = ttk.Button(self.root, text="Pause", command=self.pause_recording, state=tk.DISABLED)
        self.pause_btn.pack(pady=10)

        self.stop_btn = ttk.Button(self.root, text="Stop Recording", command=self.stop_recording, state=tk.DISABLED)
        self.stop_btn.pack(pady=10)

        self.monitor_label = ttk.Label(self.root, text="Select Monitor:")
        self.monitor_label.pack(pady=10)

        self.monitor_selector = ttk.Combobox(self.root, values=self.monitor_list)
        self.monitor_selector.current(0)
        self.monitor_selector.pack(pady=10)

        # Preview Canvas
        self.canvas = tk.Canvas(self.root, width=400, height=300)
        self.canvas.pack(pady=10)

    def get_monitors(self):
        """ Detect all available monitors """
        monitors = get_monitors()
        return [f"Monitor {i+1}: {m.width}x{m.height}" for i, m in enumerate(monitors)]

    def start_recording(self):
        """ Start screen and audio recording """
        self.recording = True
        self.paused = False
        self.screen_size = get_monitors()[self.monitor_selector.current()].width, get_monitors()[self.monitor_selector.current()].height
        
        # Video writer setup
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        self.out = cv2.VideoWriter("output.avi", fourcc, 20.0, self.screen_size)

        # Start audio and video threads
        self.audio_frames = []
        self.audio_thread = threading.Thread(target=self.record_audio)
        self.video_thread = threading.Thread(target=self.record_screen)

        self.audio_thread.start()
        self.video_thread.start()

        self.record_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.NORMAL)

    def pause_recording(self):
        """ Pause or resume recording """
        if self.paused:
            self.paused = False
            self.pause_btn.config(text="Pause")
        else:
            self.paused = True
            self.pause_btn.config(text="Resume")

    def stop_recording(self):
        """ Stop recording and save output """
        self.recording = False
        self.video_thread.join()
        self.audio_thread.join()

        self.record_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        
        # Stop and save video and audio
        self.out.release()
        self.save_audio_file()

        # Combine audio and video using FFmpeg
        self.combine_audio_video("output.avi", "output_audio.wav", "final_output.mp4")

        print("Recording saved as 'final_output.mp4'")

    def record_audio(self):
        """ Capture audio using PyAudio """
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)

        while self.recording:
            if not self.paused:
                data = stream.read(1024)
                self.audio_frames.append(data)

        stream.stop_stream()
        stream.close()
        p.terminate()

        # Save audio to file
        wf = wave.open("output_audio.wav", 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(44100)
        wf.writeframes(b''.join(self.audio_frames))
        wf.close()

    def record_screen(self):
        """ Capture the screen and update preview """
        start_time = time.time()
        while self.recording:
            if not self.paused:
                img = pyautogui.screenshot(region=(0, 0, self.screen_size[0], self.screen_size[1]))
                frame = np.array(img)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.out.write(frame)
                
                # Display the preview in the canvas
                self.update_preview(frame)

            if time.time() - start_time > 60:  # Automatically stop after 60 seconds
                self.recording = False

    def update_preview(self, frame):
        """ Update the canvas to mirror the screen recording """
        frame = cv2.resize(frame, (400, 300))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        img = cv2.flip(img, 1)
        self.preview_img = tk.PhotoImage(data=cv2.imencode('.ppm', img)[1].tobytes())
        self.canvas.create_image(0, 0, image=self.preview_img, anchor=tk.NW)

    def save_audio_file(self):
        """ Save audio to a WAV file """
        wf = wave.open("output_audio.wav", 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 2 bytes per sample (16-bit audio)
        wf.setframerate(44100)
        wf.writeframes(b''.join(self.audio_frames))
        wf.close()

    def combine_audio_video(self, video_file, audio_file, output_file):
        """ Use FFmpeg to combine audio and video files """
        os.system(f"ffmpeg -i {video_file} -i {audio_file} -c:v copy -c:a aac -strict experimental {output_file}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenRecorderApp(root)
    root.mainloop()
