from main_window import MainWindow

DEBUG = False


if __name__ == '__main__':
    main_window = MainWindow(debug=DEBUG)
    main_window.mainloop()
