# The purpose of this challenge is to stimulate the comprehension and resolution of what is being asked to do.
# In this case: identify the correct square color based on text tip.
import tkinter as tk
from tkinter import messagebox
import random
from PIL import Image, ImageTk
import numpy as np


from puzzle_data import PRIMARY_COLOR_DATA


# mover a janela de puzzle pra k
# criar uma classe principal visto que a janela dos puzzles vai sempre ter as mesmas caracteristicas
# criar maneira de pegar qual foi o teste
# qual foi o problema apresentado
# qual o resultado


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


def create_challenge_data():
    choices = random.sample(list(PRIMARY_COLOR_DATA.keys()), 3)
    correct_choice = random.choice(choices)
    return {'choices': choices, 'correct_choice': correct_choice}


def method_name(color_choices, btn_height, btn_width):
    btn_color_choices = {}
    for choice in color_choices:
        btn_color_choices[choice] = ImageTk.PhotoImage(
            Image.fromarray(
                create_image_array(
                    shape=(btn_height, btn_width),
                    rgb=PRIMARY_COLOR_DATA[choice]["rgb_code"]
                )
            )
        )
    return btn_color_choices


class BoxColor(tk.Toplevel):
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self._parent_window = parent_window

        self.attributes('-topmost', True)
        self.resizable(False, False)

        window_width, window_height, window_x, window_y = self.get_geometry_coordinates()
        self.geometry("{}x{}+{}+{}".format(window_width, window_height, window_x, window_y))

        self._btn_height = int(window_height * 0.40)  # 200 +-
        self._btn_width = int(window_width * 0.25)  # 200 +-

        self._challenge_data = create_challenge_data()

        self._btn_color_choices = method_name(self._challenge_data['choices'], self._btn_height, self._btn_width)

        self.title("Janela de perguntas")
        self.configure_window(window_width, window_height)
        self.deiconify()

    def get_geometry_coordinates(self):
        w = int(self._parent_window.winfo_width() * 0.58)  # 800 +-
        h = int(self._parent_window.winfo_height() * 0.65)  # 500 +-

        x = self._parent_window.winfo_rootx() + (self._parent_window.winfo_width() - w) // 2
        y = self._parent_window.winfo_rooty() + (self._parent_window.winfo_height() - h) // 2

        return w, h, x, y

    def configure_window(self, window_width, window_height):
        choices_len = len(self._challenge_data['choices'])
        space_between_buttons = (
            # precisa ser len + 1 por conta do ultimo espaco
            window_width - (self._btn_width * choices_len)) / (choices_len + 1)
        space = space_between_buttons

        tk.Label(
            self,
            text=f"Qual é o quadrado {PRIMARY_COLOR_DATA[self._challenge_data['correct_choice']]['name']} ?",
            border=True,
            font=('Arial', 25),
            pady=40
        ).pack()

        btn_answers = {}
        for choice in self._challenge_data['choices']:
            btn_answers[choice] = lambda selected_answer=choice: self.collect_data(self._challenge_data['choices'],
                                                                                   self._challenge_data['correct_choice'],
                                                                                   selected_answer)

        btn_objects = {}
        for choice in self._challenge_data['choices']:
            btn_objects[choice] = tk.Button(
                self,
                image=self._btn_color_choices[choice],
                command=btn_answers[choice]
            )
            btn_objects[choice].place(x=space, y=(window_height / 2) - (self._btn_height / 2))
            space += self._btn_width + space_between_buttons

    def collect_data(self, choices, correct_choice, answer):
        self._parent_window.set_result_challenge_placeholder(
            {
                'choices': choices,
                'correct_choice': correct_choice,
                'answer': answer
            }
        )
        self.destroy()
