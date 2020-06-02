import os

from flask import Flask, session, request, render_template, redirect, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests
from database_queries import *
from typing import Any

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

registryEntryTypes = ["emptyEntry", "usrNotAvailable", "pswNotMatched", "pswLength"]
loginEntryTypes = ["incorrectEntry", "registerSuccess"]
GR_KEY = "0rOvKU12KTKD5IqMr74A"

# Sign in page
@app.route("/", methods=["GET", "POST"])
def index():
    init_session_variable(varName="entries", initVal=[])
    init_session_variable(varName="username", initVal="")

    remove_entries(fr=session["entries"], entries=registryEntryTypes)

    if request.method == "GET" and len(session["username"]) == 0:
        return render_template("index.html", entries=session["entries"], page_name="index")
    elif request.method == "POST":
        usr = request.form.get("username")
        psw = request.form.get("password")

        if check_usr_password(db=db, usr=usr, psw=psw):
            session["entries"] = []
            session["username"] = usr
            return redirect(url_for('search'))
        else:
            remove_entries(session["entries"], ["registerSuccess"])
            add_entry(session["entries"], "incorrectEntry")
            return redirect(url_for('index'))
    else:
        return redirect(url_for('search'))


@app.route("/register", methods=["GET", "POST"])
def register():

    remove_entries(fr=session["entries"], entries=loginEntryTypes)

    if request.method == "GET":
        return render_template("register.html", entries=session["entries"], page_name="register")
    else:
        # if request.method == "POST"
        usr = request.form.get("username")
        psw = request.form.get("password")
        psw_confirm = request.form.get("cpassword")
        incorrectEntries = check_registry(db=db, usr=usr, psw=psw, psw_confirm=psw_confirm)

        if len(incorrectEntries) == 0:
            add_entry(session["entries"], "registerSuccess")
            add_new_user(db=db, usr=usr, psw=psw)
            return redirect(url_for('index'))

        session["entries"] = incorrectEntries
        return redirect(url_for('register'))

@app.route("/logout", methods=["POST"])
def logout():
    session["username"] = ""
    session["entries"] = []
    session["search results"] = ""
    return redirect(url_for('index'))


@app.route("/search", methods=["GET", "POST"])
def search():
    init_session_variable(varName="search results", initVal="")

    session["entries"] = []
    usr = session["username"]

    if usr == "":
        return redirect(url_for('index'))
    elif request.method == "GET":
        return render_template("search.html")
    else:
        return redirect(url_for('search_results', search=request.form.get("search")))


@app.route("/search-<string:search>", methods=["GET"])
def search_results(search):
    if (session.get("username")is None) or session["username"] == "":
        return redirect(url_for('index'))

    title = search_title(db, like=search)
    author = search_author(db, like=search)
    isbn = search_isbn(db, like=search)
    return render_template("search-results.html", title=title, author=author, isbn=isbn)


@app.route("/book/<string:isbn>", methods=["GET"])
def book(isbn):

    session["entries"] = []

    # the user must be signed in to see the data
    if (session.get("username")is None) or session["username"] == "":
        return redirect(url_for('index'))

    book_data=get_book_isbn(db, isbn=isbn)

    if book_data is None:
        return "Book with isbn "+ isbn + "was not found", 404

    gr_rating = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": GR_KEY, "isbns": isbn})

    if gr_rating.status_code != 200:
        gr_rating = None
    else:
        gr_rating = gr_rating.json()["books"][0]
        gr_rating = {"average": gr_rating["average_rating"], "count": gr_rating["work_ratings_count"]}

    reviews = get_reviews_of_book(db, isbn=isbn)
    average = 0
    for review in reviews:
        average += review.rating
    if len(reviews) != 0:
        average /= len(reviews)

    imp_books_rating = {"count": len(reviews), "average": average}
    disabled_review = user_has_reviewed(db, usr=session["username"], book_id=book_data.id)
    return render_template('book.html', book_data=book_data, goodreads_rating=gr_rating, imp_books_rating=imp_books_rating, reviews=reviews, disabled_review=disabled_review)


@app.route("/book/<string:isbn>/review", methods=["GET"])
def review(isbn):
    if (session.get("username")is None) or session["username"] == "":
        return redirect(url_for('index'))

    title = get_book_isbn(db, isbn=isbn).title
    return render_template('review.html', title=title, isbn=isbn)


@app.route("/book/<string:isbn>/review/submit", methods=["POST"])
def submit_review(isbn):
    review = request.form.get("review")
    rating = request.form.get("rating")
    usr_id = get_usr_id(db, usr=session["username"])
    book_id = get_book_isbn(db, isbn=isbn).id

    insert_review(db, {"review": review, "rating": rating, "user_id": usr_id, "book_id": book_id})
    return redirect(url_for('book', isbn=isbn))


@app.route("/api/<string:isbn>", methods=["GET"])
def api(isbn):
    api_return = {}
    book_data=get_book_isbn(db, isbn=isbn)

    if book_data is None:
        return "Book with isbn "+ isbn + "was not found", 404

    api_return["title"] = book_data.title
    api_return["author"] = book_data.author
    api_return["year"] = book_data.year
    api_return["isbn"] = book_data.isbn

    api_return["review_count"] = 0
    api_return["average_score"] = 0
    gr_rating = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": GR_KEY, "isbns": isbn})

    if gr_rating.status_code == 200:
        gr_rating = gr_rating.json()["books"][0]
        api_return["review_count"] += int(gr_rating["work_ratings_count"])
        api_return["average_score"] += float(gr_rating["average_rating"]) * api_return["review_count"]

    reviews = get_reviews_of_book(db, isbn=isbn)
    api_return["review_count"] += len(reviews)
    for review in reviews:
        api_return["average_score"] += review.rating
    if api_return["review_count"] != 0:
        api_return["average_score"] /= api_return["review_count"]

    return jsonify(api_return)




def init_session_variable(varName: str, initVal: Any):
    if session.get(varName) is None:
        session[varName] = initVal


def remove_entries(fr, entries):
    for entry in entries:
        if entry in fr:
            fr.remove(entry)


def add_entry(to, entry):
    if entry not in to:
        to.append(entry)
