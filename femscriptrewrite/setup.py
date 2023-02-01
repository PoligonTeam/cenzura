from distutils.core import setup, Extension

def main():
    setup(
        name = "femscript",
        ext_modules = [
            Extension("femscript", ["femscript.c"])
        ]
    )

if __name__ == "__main__":
    main()
