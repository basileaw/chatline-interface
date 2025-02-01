from chatline import Interface

def main():
    chat = Interface.from_args() # Uses default local generator
    chat.preface("Welcome to ChatLine", color="BLUE")
    chat.start()

if __name__ == "__main__":
    main()