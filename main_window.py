import tkinter as tk
import customtkinter

from screeninfo import get_monitors


from challenges.box_color import BoxColor


def get_primary_monitor():
    for monitor in get_monitors():
        if monitor.is_primary:
            return monitor


class MainWindow(customtkinter.CTk):
    def __init__(self, debug: bool = False):
        super().__init__()
        self.__debug = debug

        self.__monitor_info = get_primary_monitor()

        self.configure(
            width=self.__monitor_info.width,
            height=self.__monitor_info.height
        )
        self.wait_visibility(self)
        self.wm_attributes("-alpha", .5)
        self.geometry(
            f"{self.__monitor_info.width}x{self.__monitor_info.height}+{self.__monitor_info.x}+{self.__monitor_info.y}"
        )

        if self.__debug:
            exit_btn = tk.Button(
                self,
                text="close",
                command=lambda: self.quit())
            exit_btn.place(x=10, y=10)

        self._result_challenge_placeholder = None

        self.open_window()

    def set_result_challenge_placeholder(self, answer_data):
        self._result_challenge_placeholder = answer_data

    def open_window(self):
        box_color = BoxColor(self)
        self.wait_window(box_color)
        print(self._result_challenge_placeholder)
        self.destroy()
