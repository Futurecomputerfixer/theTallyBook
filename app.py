from flask import Flask, render_template, request, session, redirect, json
from flask_session.__init__ import Session
from tempfile import mkdtemp
from functools import wraps
from helpers import connect
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = "dev"

# no cache
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)



# require the user to be logged in to make moves
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function




# error manipulation
apology = None


# main-page
@app.route("/")
@login_required
def index():

    conn = connect()
    cur = conn.cursor()

    # greet the user in the mainpage
    cur.execute("""SELECT username FROM "user" WHERE id = ?""", (session["user_id"],))
    username = cur.fetchall()

    #return all entries of the current user
    cur.execute("SELECT * FROM entry WHERE user_id = ? ORDER BY entry_date", (session["user_id"],))
    tmp = cur.fetchall()

    # if the user has no entry yet 
    if not tmp:
        conn.close()
        return render_template("index.html", apology="NOT ENTRY YET, CLICK UPLEFT CORNOR TO CREATE A NEW ENTRY",user=username[0][0])

    # transform the entries to html-friendly lists 
    entries = []
    for entry in tmp:
        cur.execute("SELECT category FROM category WHERE user_id = ? AND id = ?", (session["user_id"], entry[2]))
        category = cur.fetchall()
        entry_list = list(entry)
        entry_list.append(category[0][0])
        entries.append(entry_list)

    
    conn.close()

    return render_template("index.html", apology=apology, entries=entries, user=username[0][0])



# webpage for creating new category of entry
@app.route("/category", methods=["GET", "POST"])
@login_required
def category():
    if request.method == "POST":
        # check if the submitted category already exist
        conn = connect()
        cur = conn.cursor()
        cur.execute("SELECT category FROM category WHERE user_id = ?", (session["user_id"],))   
        rows = cur.fetchall()  
        category_list = []
        for row in rows:
            category_list.append(row[0])
        category = request.form.get("category")

        if category in category_list: # the category already exists, return error 
            conn.close()
            return render_template("category.html", apology="THE CATEGORY ALREADY EXISTS")
        else: # store new category in the database
            cur.execute("INSERT INTO category(category, user_id)VALUES(?, ?)", (category, session["user_id"]))
            
            conn.commit()
            conn.close()

            return redirect("/entry")

    else:
        return render_template("category.html", apology=None)



@app.route("/entry", methods=["GET", "POST"] )
@login_required
def entry():
    if request.method == "POST":
        # access to the database 
        conn = connect()
        cur = conn.cursor()

        # retrieve data from the submitted form
        category = request.form.get("Category")
        description = request.form.get("description")
        amount = request.form.get("amount")
        date = request.form.get("date")

        # store new entry into the database
        cur.execute("SELECT id FROM category WHERE category = ? AND user_id = ?", (category, session["user_id"]))
        id = cur.fetchall()
        cur.execute("INSERT INTO entry(description, amount, category_id, user_id, entry_date) VALUES(?, ?, ?, ?, ?)", (description, amount, id[0][0], session["user_id"], date))
        
        conn.commit()
        conn.close()

        return redirect("/")
    else:
        # access to the database 
        conn = connect()
        cur = conn.cursor()
        cur.execute("SELECT category FROM category WHERE user_id = ?", (session["user_id"], ))
        categories = cur.fetchall()

        return render_template("entry.html", categories=categories)





# login page. all users first time accessing the website will be redirect to this 
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("login.html", apology="Must Provide Username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("login.html", apology="Must Provide Password")

        # connect to the database
        conn = connect()
        cur = conn.cursor()
        # execute a statement
        cur.execute("""SELECT id, hash FROM "user" WHERE username = ?""", (request.form.get("username"), ))   
        # fetch data from database then close it
        rows = cur.fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][1], request.form.get("password")):
            return render_template("login.html", apology="Invalid Username and/or Password")

        # Remember which user has logged in
        session["user_id"] = rows[0][0]
        conn.close()

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html", apology=apology)



# log the user out
@app.route("/logout")
def logout():
    # log the user out
    session.clear()
    # return to login
    return redirect("/")



# signup page
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        # query the database
        conn = connect()
        cur = conn.cursor()
        username = request.form.get("username")
        
        # error checking
        # check if the username is blank 
        if not username:
            conn.close()
            return render_template("signup.html", apology="The Username Field Cannot be blank")
        
        # check for the passowords field
        elif not request.form.get("password") or not request.form.get("confirmation"):
            conn.close()
            return render_template("signup.html", apology="The Passoword Fields Cannot Be Blank")

        elif not request.form.get("password") == request.form.get("confirmation"):
            conn.close()
            return render_template("signup.html", apology="The Passwords Need to Be the Same")

        # check if any other user uses the same username
        cur.execute("""SELECT * FROM "user" WHERE username = ?""", (username,)) 
        if cur.fetchall():
            conn.close()
            return render_template("signup.html", apology="The Username Already Exists")

        # hash password and create new user account 
        hash = generate_password_hash(request.form.get("password"))
        cur.execute("""INSERT INTO "user" (username, hash) VALUES(?, ?)""", (request.form.get("username"), hash))
        cur.execute("""SELECT id FROM "user" WHERE username = ?""", (username,))
        
        # log the user in
        rows = cur.fetchall()
        session["user_id"] = rows[0][0]
        
        conn.commit()
        conn.close()
        
        return redirect("/")
    else: 
        return render_template("signup.html", apology=apology)


# the lil pie chart 
@app.route("/summary")
@login_required
def summary():
    """display monthly spending"""
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id, category FROM category WHERE user_id = ?", (session["user_id"],))   
    rows = cur.fetchall()  
    summary = []

    for row in rows:
        cur.execute("SELECT SUM(AMOUNT) FROM entry WHERE user_id = ? AND category_id = ?", (session["user_id"], row[0]))
        sum = cur.fetchall()
        list = [row[1]] 
        list.append(sum[0][0])
        summary.append(list)

    return render_template("summary.html", summary=json.dumps(summary))



if __name__ == '__main__':
   app.run(debug = True)