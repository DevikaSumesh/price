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

# Function definitions (amazon, bookswagon, kitabay) remain unchanged

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    book_name = request.form['book_name']
    headers = {
        'User -Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.134 Safari/537.36'
    }
    session = requests.Session()

    # Fetch data from all sources
    scraped_data = [
        amazon(session, headers, book_name),
        bookswagon(session, headers, book_name),
        kitabay(session, headers, book_name)
    ]

    # Sort by price (cheapest first)
    sorted_data = sorted(scraped_data, key=lambda x: x[5])

    # Insert data into the database
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

    return jsonify(sorted_data)

if __name__ == '__main__':
    app.run(debug=True)
