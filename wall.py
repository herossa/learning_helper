import tkinter as tk


class Wall:
    def __init__(self, debug: bool = False):
        self.__debug = debug
        self.__root = None
        self.__window_width = None
        self.__window_height = None

    def create_main_window(self):
        if self.__root is None:
            self.__root = tk.Tk()
            self.__window_width = self.__root.winfo_screenwidth()
            self.__window_height = self.__root.winfo_screenheight()
            self.__root.configure(
                width=self.__window_width,
                height=self.__window_height
            )
            self.__root.resizable(0, 0)
            self.__root.wait_visibility(self.__root)
            self.__root.wm_attributes("-alpha", .5)
            self.__root.geometry(f"{self.__window_width}x{self.__window_height}+0+0")

            if self.__debug:
                exit_btn = tk.Button(
                    self.__root,
                    text="close",
                    command=lambda: self.__root.quit())
                exit_btn.place(x=10, y=10)
        return self.__root

    def get_window_dimensions(self):
        return self.__window_height, self.__window_width
