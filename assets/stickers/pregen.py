from PIL import Image, ImageDraw, ImageFont
import sys, os, colorsys

def main() -> None:
    font = ImageFont.truetype("../fonts/YurukaStd.woff2", 40)

    for dr in os.listdir():
        if dr == sys.argv[0]:
            continue

        files = [f"./{dr}/{file}" for file in os.listdir(dr) if file not in ("pregen.png", "color")]
        count = len(files)

        images = [Image.open(file) for file in files if file]
        sizes = [image.size for image in images]
        size = max(size[0] for size in sizes), max(size[1] for size in sizes)

        grid = count ** 0.5
        if grid % 1:
            grid = grid - grid % 1 + 1
        grid = int(grid)

        chunks = [images[i:i+grid] for i in range(0, len(images), grid)]

        canvas = Image.new("RGBA", (size[0] * grid, size[1] * grid))

        colors = []

        for image in images:
            colors.extend(image.getcolors(image.size[0] * image.size[1]) or [(0, 0, 0, 0)])

        filtered_colors = []

        for count, (r, g, b, a) in colors:
            if a > 0:
                h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)

                if 0.1 < l < 0.9:
                    filtered_colors.append((count, h))

        if filtered_colors:
            hue = max(filtered_colors, key=lambda item: item[0])[1]

            r, g, b = colorsys.hls_to_rgb(hue, 0.5, 0.5)
            color = (int(r * 255), int(g * 255), int(b * 255), 255)

        with open(f"./{dr}/color", "wb") as f:
            r, g, b, a = color
            f.write(bytes([r, g, b]))

        for row_index, row in enumerate(chunks):
            for column_index, image in enumerate(row):
                # text = image.filename.split("/")[-1].split(".")[0]
                text = str(images.index(image))
                _, _, text_width, text_height = font.getbbox(text, stroke_width=5)
                text_image = Image.new("RGBA", (text_width + 2, text_height + 2), (0, 0, 0, 0))
                draw = ImageDraw.Draw(text_image)

                draw.text((text_image.width // 2 - text_width // 2 - 1, text_image.height // 2 - text_height // 2), text, fill=(255, 255, 255, 255), stroke_width=5, stroke_fill=(255, 255, 255, 255), font=font)
                draw.text((text_image.width // 2 - text_width // 2 + 1, text_image.height // 2 - text_height // 2), text, fill=(255, 255, 255, 255), stroke_width=5, stroke_fill=(255, 255, 255, 255), font=font)
                draw.text((text_image.width // 2 - text_width // 2, text_image.height // 2 - text_height // 2 - 1), text, fill=(255, 255, 255, 255), stroke_width=5, stroke_fill=(255, 255, 255, 255), font=font)
                draw.text((text_image.width // 2 - text_width // 2, text_image.height // 2 - text_height // 2 + 1), text, fill=(255, 255, 255, 255), stroke_width=5, stroke_fill=(255, 255, 255, 255), font=font)
                draw.text((text_image.width // 2 - text_width // 2, text_image.height // 2 - text_height // 2), text, fill=color, font=font)

                text_image = text_image.rotate(10, resample=Image.BICUBIC, expand=True)

                image.paste(text_image, (image.width // 2 - text_image.width // 2, 30), mask=text_image.split()[3])

                canvas.paste(image, (size[0] * column_index, size[1] * row_index))

        canvas.save(f"./{dr}/pregen.png")

if __name__ == "__main__":
    main()