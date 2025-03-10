from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pony import orm

app = Flask(__name__)

# Set up the Database
db = orm.Database()
db.bind(provider='sqlite', filename='database6.sqlite', create_db=True)

class BookPrice(db.Entity):
    book_name = orm.Required(str)
    isbn = orm.Optional(str, nullable=True)
    author = orm.Optional(str, nullable=True)
    image_url = orm.Optional(str, nullable=True)
    website = orm.Required(str)
    price = orm.Required(float)
    date_created = orm.Required(datetime)

db.generate_mapping(create_tables=True)

# User-Agent Headers
headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.134 Safari/537.36'
}

# Function to scrape book price data
def scrape_price(url, price_selector, isbn_selector=None, author_selector=None, image_selector=None, book_name="Unknown", site_name="Unknown"):
    """
    Scrapes book details (price, ISBN, author, image) from a given website.
    """
    session = requests.Session()
    resp = session.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")

    # Extract price
    price_element = soup.select_one(price_selector)
    if price_element is None:
        return {
            "book_name": book_name,
            "isbn": None,
            "author": None,
            "image_url": "Image Not Found",
            "website": site_name,
            "price": 0.0
        }

    price_text = price_element.text.replace("₹", "").replace("Rs.", "").replace(",", "").strip()
    try:
        price = float(price_text)
    except ValueError:
        price = 0.0

    # Extract ISBN, author, and image
    isbn_element = soup.select_one(isbn_selector) if isbn_selector else None
    author_element = soup.select_one(author_selector) if author_selector else None
    image_element = soup.select_one(image_selector) if image_selector else None

    return {
        "book_name": book_name,
        "isbn": isbn_element.text.strip() if isbn_element else "Unknown",
        "author": author_element.text.strip() if author_element else "Unknown",
        "image_url": image_element['src'] if image_element else "Image Not Found",
        "website": site_name,
        "price": price
    }

# Amazon, Bookswagon, and Kitabay Scrapers
def amazon(book_name):
    return scrape_price(
        url="https://amzn.in/d/ctd5cdW",
        price_selector="span.a-price-whole",
        isbn_selector="div#detailBullets_feature_div li:contains('ISBN-13')",
        author_selector="span.author a",
        image_selector="img#landingImage",
        book_name=book_name,
        site_name="Amazon"
    )

def bookswagon(book_name):
    return scrape_price(
        url="https://www.bookswagon.com/book/little-women-louisa-may-alcott/9780099572961",
        price_selector="label#ctl00_phBody_ProductDetail_lblourPrice",
        isbn_selector="li:contains('ISBN-13')",
        author_selector="label#ctl00_phBody_ProductDetail_lblAuthor1 a",
        image_selector="img[src]",
        book_name=book_name,
        site_name="Bookswagon"
    )

def kitabay(book_name):
    return scrape_price(
        url="https://kitabay.com/products/little-women-4?_pos=1&_sid=3ea41e284&_ss=r",
        price_selector="span.product__price--sale",
        isbn_selector="p:contains('ISBN:')",
        author_selector="p:contains('Author -')",
        image_selector="img.object-cover",
        book_name=book_name,
        site_name="Kitabay"
    )

# Home Page Route
@app.route('/')
def index():
    return render_template('index.html')

# Search API Route
@app.route('/search', methods=['POST'])
def search():
    book_name = request.form['book_name']

    # Fetch data from all sources
    scraped_data = [
        amazon(book_name),
        bookswagon(book_name),
        kitabay(book_name)
    ]

    # Sort by price (cheapest first)
    sorted_data = sorted(scraped_data, key=lambda x: x["price"])

    # Insert into the database
    with orm.db_session:
        for item in sorted_data:
            BookPrice(
                book_name=item["book_name"],
                isbn=item["isbn"],
                author=item["author"],
                image_url=item["image_url"],
                website=item["website"],
                price=item["price"],
                date_created=datetime.now()
            )

    return jsonify({"book": book_name, "prices": sorted_data})

if __name__ == '__main__':
    app.run(debug=True)
