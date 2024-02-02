import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import random
from PIL import Image, ImageTk
import numpy as np

from wall import Wall
from puzzle_data import PRIMARY_COLOR_DATA

DEBUG = True


def _from_rgb(rgb):
    return "#%02x%02x%02x" % rgb


def create_image_array(shape=(20, 20), rgb=(0, 0, 0)):
    custom_image = np.zeros((shape[0], shape[1], len(rgb)), dtype=np.uint8)
    for layer, value in enumerate(rgb):
        custom_image[:, :, layer] = value
    return custom_image


def process_answer(parent_window, answer, correct_answer):
    if answer == correct_answer:
        messagebox.showinfo(
            title='Parabéns!!!',
            message='Parabéns, você acertou. Continue assim!!!',
            icon='info',
            type='ok',
            parent=parent_window
        )
        # parent_window.quit()
    else:
        messagebox.showerror(
            title='Você errou!!!',
            icon='error',
            message='Tente novamente!!!',
            type='ok',
            parent=parent_window
        )


if __name__ == '__main__':
    wall = Wall(debug=True)
    # root = wall.create_main_window()
    main_window_height, main_window_width = wall.get_window_dimensions()
    # root = tk.Tk()
    # main_window_width = root.winfo_screenwidth()
    # main_window_height = root.winfo_screenheight()
    # root.configure(
    #     width=main_window_width,
    #     height=main_window_height
    # )
    # root.resizable(0, 0)
    # root.wait_visibility(root)
    # root.wm_attributes("-alpha", .5)
    # root.geometry(f"{main_window_width}x{main_window_height}+0+0")
    #
    # if DEBUG:
    #     exit_btn = ttk.Button(
    #         root,
    #         text="close",
    #         command=lambda: root.quit())
    #     exit_btn.place(x=10, y=10)

    puzzle_window = tk.Toplevel(wall)
    # puzzle_window.overrideredirect(1)
    puzzle_window.attributes('-topmost', True)
    puzzle_window.resizable(False, False)
    puzzle_window.title("Janela de perguntas")
    puzzle_window_w = int(main_window_width * 0.58) # 800 +-
    puzzle_window_h = int(main_window_height * 0.65) # 500 +-

    # calculating the position of puzzle window
    x = (main_window_width / 2) - (puzzle_window_w / 2)
    y = (main_window_height / 2) - (puzzle_window_h / 2)

    # defining the position and size based on the previous calculations
    puzzle_window.geometry('%dx%d+%d+%d' % (main_window_width, main_window_height, x, y))

    puzzle_window.geometry(f"{puzzle_window_w}x{puzzle_window_h}")

    # creating puzzle buttons
    # generating possible colors for buttons
    choices = random.sample(list(PRIMARY_COLOR_DATA.keys()), 3)
    correct_choice = random.choice(choices)

    btn_window_w = int(puzzle_window_w * 0.25)  # 200 +-
    btn_window_h = int(puzzle_window_h * 0.40)  # 200 +-

    space_between_buttons = (puzzle_window_w - (btn_window_w * len(choices))) / (len(choices) + 1) # precisa ser len + 1 por conta do ultimo espaco
    space = space_between_buttons

    tk.Label(
        puzzle_window,
        text=f"Qual é o quadrado {PRIMARY_COLOR_DATA[correct_choice]['name']} ?",
        border=True,
        font=('Arial', 25),
        pady=40
    ).pack()

    btn_choices = {}
    for choice in choices:
        btn_choices[choice] = ImageTk.PhotoImage(Image.fromarray(
            create_image_array(
                shape=(btn_window_h, btn_window_w),
                rgb=PRIMARY_COLOR_DATA[choice]["rgb_code"]
            )
        ))

    btn_answers = {}
    for choice in choices:
        btn_answers[choice] = lambda ch=choice: process_answer(puzzle_window, ch, correct_choice)

    btns = {}
    for choice in choices:
        btns[choice] = tk.Button(
            puzzle_window,
            image=btn_choices[choice],
            command=btn_answers[choice]
        )
        btns[choice].place(x=space, y=(puzzle_window_h / 2) - (btn_window_h / 2))
        space += btn_window_w + space_between_buttons
    puzzle_window.deiconify()

    wall.mainloop()
