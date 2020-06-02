
from sqlalchemy import text

def check_usr_password(db, usr: str, psw: str) -> bool:
    if str == "" or psw == "":
        return False

    users = db.execute("SELECT username, password FROM users WHERE username=:usr", {"usr": usr}).fetchone()

    if (users is None) or (users.password != psw):
        return False
    return True


def check_registry(db, usr: str, psw: str, psw_confirm: str) -> str:
    if str == "" or psw == "" or psw_confirm == "":
        return ["emptyEntry"]

    lst = []
    existingUsr = db.execute("SELECT username FROM users WHERE username=:usr", {"usr": usr}).fetchone()

    if existingUsr is not None:
        lst.append("usrNotAvailable")

    if psw != psw_confirm:
        lst.append("pswNotMatched")

    if not (8 <= len(psw) <= 24):
        lst.append("pswLength")
    return lst


def add_new_user(db, usr: str, psw: str):
    db.execute("INSERT INTO users (username, password) VALUES (:usr, :psw)", {"usr": usr, "psw": psw})
    db.commit()


def search_title(db, like: str):
    result = like.split(" ")
    like = ""
    for i in range(len(result)):
        if result[i] not in ["and"]:
            like += result[i].capitalize()
        else:
            like += result[i]

        if i != len(result) - 1:
            like += " "
    like = '%'+like+'%'
    return db.execute(text("SELECT * FROM books WHERE title LIKE :like ORDER BY title ASC"), {"like": like}).fetchall()


def search_author(db, like: str):
    result = like.split(" ")
    like = ""
    for i in range(len(result)):
        if result[i] not in ["and"]:
            like += result[i].capitalize()
        else:
            like += result[i]

        if i != len(result) - 1:
            like += " "
    like = '%'+like+'%'
    return db.execute(text("SELECT * FROM books WHERE author LIKE :like ORDER BY author ASC"), {"like": like}).fetchall()


def search_isbn(db, like: str):
    result = like.split(" ")
    like = ""
    for i in range(len(result)):
        if result[i] not in ["and"]:
            like += result[i].capitalize()
        else:
            like += result[i]

        if i != len(result) - 1:
            like += " "

    like = '%'+like+'%'
    return db.execute(text("SELECT * FROM books WHERE isbn LIKE :like ORDER BY isbn ASC"), {"like": like}).fetchall()


def get_book_isbn(db, isbn: str):
    return db.execute("SELECT * FROM books WHERE isbn=:isbn", {"isbn":isbn}).fetchone()


def get_reviews_of_book(db, isbn:str):
    book_id = db.execute("SELECT * FROM books WHERE isbn=:isbn", {"isbn": isbn}).fetchone().id
    reviews = db.execute("SELECT * FROM reviews JOIN users ON reviews.user_id=users.id WHERE book_id=:book_id ORDER BY reviews.id DESC", {"book_id": book_id}).fetchall()
    return reviews


def get_usr_id(db, usr: str):
    user = db.execute("SELECT * FROM users WHERE username=:usr", {"usr": usr}).fetchone()
    if user is None:
        print("user does not exist")
        exit(1)
    return user.id


def insert_review(db, review_data: dict):
    db.execute("INSERT INTO reviews (review, rating, book_id, user_id) VALUES (:review, :rating, :book_id, :user_id)", review_data)
    db.commit()


def user_has_reviewed(db, usr: str, book_id: int):
    user_id = get_usr_id(db, usr)
    return db.execute("SELECT * FROM reviews WHERE (user_id=:user_id AND book_id=:book_id)", {"user_id": user_id, "book_id": book_id }).fetchone() is not None
