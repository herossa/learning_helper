import tkinter as tk


class Wall(tk.Tk):
    def __init__(self, debug: bool = False):
        super().__init__()
        self.__debug = debug

        self.configure(
            width=self.winfo_screenwidth(),
            height=self.winfo_screenheight()
        )
        self.resizable(False, False)
        self.wait_visibility(self)
        self.wm_attributes("-alpha", .5)
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")

        if self.__debug:
            exit_btn = tk.Button(
                self,
                text="close",
                command=lambda: self.quit())
            exit_btn.place(x=10, y=10)

    def get_window_dimensions(self):
        return self.winfo_screenheight(), self.winfo_screenwidth()
