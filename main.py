from typing import List
import os
import glob
import asyncio
import csv
from hashlib import sha1
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
import click
from pyppeteer import launch
from PIL import Image
from jinja2 import Template


@dataclass(frozen=True)
class Product():
    name: str
    url: str
    categories: List[str]
    description: str
    tags: List[str]

    @property
    def image_name(self):
        return sha1(self.url.encode('utf-8')).hexdigest()


def load_products_csv() -> List[Product]:
    products = []
    def parse_list(list_str: str) -> List[str]:
        return [s.strip() for s in list_str.split('+')]
    with open('data/data.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        next(csv_reader)
        for row in csv_reader:
            p = Product(
                name=row[0],
                url=row[1],
                categories=parse_list(row[2]),
                description=row[3],
                tags=parse_list(row[4])
            )
            products.append(p)
    return products


async def capture_screenshots(websites: List[str]) -> None:
    browser = await launch()
    page = await browser.newPage()
    await page.setViewport({'width': 1200, 'height': 800})
    for website in websites:
        filename = sha1(website.encode('utf-8')).hexdigest()
        if not os.path.exists(f'processing/screenshots/{filename}.png'):
            await page.goto(website)
            await page.screenshot({'path': f'processing/screenshots/{filename}.png'})
    await browser.close()


def resize_all_screenshots() -> None:
    size = 600, 400
    for filepath in glob.glob("processing/screenshots/*.png"):
        im = Image.open(filepath)
        im.thumbnail(size)
        name = os.path.basename(filepath)
        im.save('processing/screenshot_thumbnails/' + name, 'PNG')


@click.group()
def cli():
    pass


@cli.command()
def generate():
    click.echo("Generating...")
    products: List[Product] = load_products_csv()
    categories = defaultdict(list)
    for product in products:
        for category in product.categories:
            categories[category].append(product)
    urls = [p.url for p in products]
    asyncio.get_event_loop().run_until_complete(capture_screenshots(urls))
    resize_all_screenshots()
    with open(Path('templates/index.htm')) as template_file:
        template = Template(template_file.read())
        with open(Path('index.html'), 'w') as index_file:
            index_file.write(template.render(categories=categories, category_keys=sorted(categories.keys())))

if __name__ == "__main__":
    cli()