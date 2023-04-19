import socket
from PIL import Image
from io import BytesIO
from kivy.app import App
from kivy.uix.image import Image as KivyImage
from kivy.clock import Clock
from threading import Thread

class ScreenViewer(KivyImage):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.index = 0
        self.frames = []

    def receive_frames(self):
        while True:
            data, _ = self.socket.recvfrom(65535) # assuming MTU is 65535
            image = Image.open(BytesIO(data))
            self.frames.append(image)

    def update_frame(self, dt):
        if self.index < len(self.frames):
            self.texture = self.frames[self.index].texture
            self.index += 1

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            Clock.schedule_interval(self.update_frame, 1/30) # assuming 30 fps
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            Clock.unschedule(self.update_frame)
            return True
        return super().on_touch_up(touch)

class MyApp(App):
    def build(self):
        viewer = ScreenViewer()
        viewer.socket.bind(('192.168.143.46', 1234)) # listen on port 1234
        receive_thread = Thread(target=viewer.receive_frames)
        receive_thread.daemon = True
        receive_thread.start()
        return viewer

MyApp().run()
