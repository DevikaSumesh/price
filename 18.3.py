import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pony import orm
import time

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

def amazon(session, headers, book_name):
    url = "https://amzn.in/d/ctd5cdW"
    resp = session.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")

    whole_price_element = soup.select_one("span.a-price-whole")
    fraction_price_element = soup.select_one("span.a-price-fraction")
    author_element = soup.select_one("span.author a")

    # ✅ Extract Image URL
    image_element = soup.find("img", id="landingImage") or soup.find("img", class_="frontImage")
    image_url = image_element['src'] if image_element else "Image Not Found"

    # ✅ Extract ISBN-13
    isbn = None
    product_details = soup.find("div", {"id": "detailBullets_feature_div"})
    if product_details:
        for li in product_details.find_all("li"):
            text = li.get_text(strip=True)
            if "ISBN-13" in text:
                isbn = text.split(":")[-1].strip()
                break

    if not isbn:
        product_table = soup.find("table", {"id": "productDetailsTable"})
        if product_table:
            for row in product_table.find_all("tr"):
                text = row.get_text(strip=True)
                if "ISBN-13" in text:
                    isbn = text.split(":")[-1].strip()
                    break

    if whole_price_element is None:
        return book_name, isbn, None, image_url, "amazon", 0.0

    whole_price = whole_price_element.text.replace(",", "").strip()
    fraction_price = fraction_price_element.text.strip() if fraction_price_element else "00"
    price_text = f"{whole_price}.{fraction_price}"

    try:
        price = float(price_text)
    except ValueError:
        price = 0.0

    author = author_element.text.strip() if author_element else "Unknown"

    return book_name, isbn, author, image_url, "amazon", price

def bookswagon(session, headers, book_name):
    search_url = f"https://www.bookswagon.com/search-books/{'+'.join(book_name.split())}"
    resp = session.get(search_url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    first_result = soup.select_one(".title a")
    if not first_result:
        return None
    
    book_url = first_result['href']
    time.sleep(2)
    resp = session.get(book_url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    price_element = soup.find("label", id="ctl00_phBody_ProductDetail_lblourPrice")
    image_element = soup.find("img", src=True)
    author_element = soup.select_one("label#ctl00_phBody_ProductDetail_lblAuthor1 a")
    
    price = float(price_element.text.replace("₹", "").replace(",", "").strip()) if price_element else 0.0
    image_url = image_element['src'] if image_element else "Image Not Found"
    author = author_element.text.strip() if author_element else "Unknown"
    
    return book_name, None, author, image_url, "Bookswagon", price

def kitabay(session, headers, book_name):
    url = "https://kitabay.com/products/little-women-4?_pos=1&_sid=3ea41e284&_ss=r"
    resp = session.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")

    price_element = soup.find("span", class_="product__price--sale")

    # ✅ Extract Image URL
    image_element = soup.find("img", class_="object-cover")
    image_url = image_element['src'] if image_element else "Image Not Found"

    author_element = soup.find("p", string=lambda text: text and "Author -" in text)
    author = author_element.text.replace("Author -", "").strip() if author_element else "Unknown"

    isbn_element = soup.find("p", string=lambda text: text and "ISBN:" in text)
    isbn = isbn_element.text.replace("ISBN:", "").strip() if isbn_element else "Unknown"

    if price_element is None:
        return book_name, None, None, image_url, "kitabay", 0.0

    price_text = price_element.text.replace("Rs.", "").replace(",", "").strip()
    
    try:
        price = float(price_text)
    except ValueError:
        price = 0.0

    return book_name, isbn, author, image_url, "kitabay", price

def main():
    book_name = input("Enter the book name: ")
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.134 Safari/537.36'
    }
    session = requests.Session()

    # ✅ Fetch data from all sources
    scraped_data = [
        amazon(session, headers, book_name),
        bookswagon(session, headers, book_name),
        kitabay(session, headers, book_name)
    ]

    # ✅ Sort by price (cheapest first)
    sorted_data = sorted(scraped_data, key=lambda x: x[5])

    for item in sorted_data:
        print(f"{item[0]} - {item[4]}: ₹{item[5]} (ISBN: {item[1]}, Author: {item[2]}, Image: {item[3]})")

    # ✅ Insert data into the database
    with orm.db_session:
        for item in sorted_data:
            BookPrice(
                book_name=item[0],
                isbn=item[1],
                author=item[2],
                image_url=item[3],
                website=item[4],
                price=item[5],
                date_created=datetime.now()
            )

    print("\n✅ Data successfully saved to the database!")

if __name__ == '__main__':
    main()
