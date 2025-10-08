from flask import Flask, render_template, request, redirect, session, flash
import os
from werkzeug.utils import secure_filename

from dotenv import load_dotenv
import os

load_dotenv(dotenv_path="bid_bridge.env")  # specify your .env file


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key')



# Database connection
import os
import psycopg2
from urllib.parse import urlparse  # ✅ import urlparse

def get_db_connection():
    url = urlparse(os.environ['DATABASE_URL'])

    conn = psycopg2.connect(
        dbname=url.path[1:],       # remove leading '/'
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port,
        sslmode='require'
    )
    return conn

# Set the upload folder
UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    items = []
    bids = {}
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get all items with highest bid and bidder
        cursor.execute('''
           SELECT 
               i.item_id, 
               i.item_name, 
               i.description, 
               i.age, 
               i.starting_price, 
               i.image_path,
               u.name AS owner_name,
               highest_bid_data.highest_bid,
               ub.name AS highest_bidder
           FROM items i
           JOIN users u ON i.user_id = u.user_id
           LEFT JOIN (
               SELECT 
                   item_id, 
                   MAX(bid_amount) AS highest_bid 
               FROM bids 
               GROUP BY item_id
           ) AS highest_bid_data ON i.item_id = highest_bid_data.item_id
           LEFT JOIN bids b ON highest_bid_data.item_id = b.item_id AND highest_bid_data.highest_bid = b.bid_amount
           LEFT JOIN users ub ON b.user_id = ub.user_id
           WHERE i.auction_ended = FALSE
        ''')
        items = cursor.fetchall()
        
        # All bids
        cursor.execute('''
            SELECT b.item_id, b.bid_amount, u.name AS bidder_name
            FROM bids b
            JOIN users u ON b.user_id = u.user_id
            ORDER BY b.item_id, b.bid_amount DESC
        ''')
        all_bids = cursor.fetchall()
        
        for bid in all_bids:
            item_id = bid[0]
            if item_id not in bids:
                bids[item_id] = []
            bids[item_id].append({
                'bid_amount': bid[1],
                'bidder_name': bid[2]
            })
    
    return render_template('home.html', items=items, bids=bids)

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s', (email, password))
            user = cursor.fetchone()
            if user:
                session['user_id'] = user[0]
                session['user_name'] = user[1]
                session['email'] = user[2]
                flash('Login successful!', 'success')
                return redirect('/')
            else:
                flash('Invalid email or password.', 'danger')
    return render_template('login.html')

# Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        mobile_number = request.form['mobile_number']
        address = request.form['address']
        password = request.form['password']
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (name, email, mobile_number, address, password) VALUES (%s, %s, %s, %s, %s)',
                           (name, email, mobile_number, address, password))
            conn.commit()
            flash('Registered successfully! Please log in.', 'success')
            return redirect('/login')
    return render_template('registration.html')

# Profile
@app.route('/profile')
def profile():
    if 'email' not in session:
        return redirect('/login')

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = %s', (session['email'],))
        user = cursor.fetchone()

        if not user:
            return redirect('/login')

        # User items
        cursor.execute('''
           SELECT i.item_id, i.item_name, i.starting_price, i.sold_price, u.name AS winner_name
           FROM items i
           LEFT JOIN users u ON i.sold_to = u.user_id
           WHERE i.user_id = %s
        ''', (user[0],))
        user_items = cursor.fetchall()

        # User bids
        cursor.execute('SELECT b.bid_amount, i.item_name FROM bids b JOIN items i ON b.item_id = i.item_id WHERE b.user_id = %s', (user[0],))
        user_bids = cursor.fetchall()

        # User wins
        cursor.execute('SELECT i.item_name, i.sold_price FROM items i WHERE i.sold_to = %s AND i.auction_ended = TRUE', (user[0],))
        user_wins = cursor.fetchall()

    return render_template('profile.html', user=user, user_items=user_items, user_bids=user_bids, user_wins=user_wins)

# Add Item
@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if 'user_id' not in session:
        return redirect('/login')
    
    if request.method == 'POST':
        item_name = request.form['item_name']
        age = request.form['age']
        description = request.form['description']
        starting_price = request.form['starting_price']
        
        # Handle image upload
        image_path = None
        if 'image' in request.files:
            image = request.files['image']
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                image_path = os.path.join(UPLOAD_FOLDER, filename)
                image.save(image_path)
        
        if not image_path:
            image_path = os.path.join(UPLOAD_FOLDER, 'default_image.jpg')
        
        relative_image_path = image_path.replace('static/', '').replace('\\', '/')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO items (item_name, age, description, starting_price, user_id, image_path) VALUES (%s, %s, %s, %s, %s, %s)',
                           (item_name, age, description, starting_price, session['user_id'], relative_image_path))
            conn.commit()
            flash('Item added successfully!', 'success')
            return redirect('/')
    
    return render_template('add_item.html')

# Bid
@app.route('/bid/<int:item_id>', methods=['POST'])
def bid(item_id):
    if 'user_id' not in session:
        return redirect('/login')

    bid_amount = request.form['bid_amount']
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO bids (item_id, user_id, bid_amount) VALUES (%s, %s, %s)',
                       (item_id, session['user_id'], bid_amount))
        conn.commit()
        flash('Bid placed successfully!', 'success')
    
    return redirect('/')

# End Auction
@app.route('/end_auction/<int:item_id>', methods=['POST'])
def end_auction(item_id):
    if 'user_id' not in session:
        return redirect('/login')
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT MAX(bid_amount) FROM bids WHERE item_id = %s', (item_id,))
        highest_bid = cursor.fetchone()
        
        if highest_bid and highest_bid[0]:
            cursor.execute('SELECT user_id FROM bids WHERE item_id = %s AND bid_amount = %s', (item_id, highest_bid[0]))
            winner = cursor.fetchone()
            if winner:
                cursor.execute('UPDATE items SET sold_to = %s, sold_price = %s, auction_ended = TRUE WHERE item_id = %s',
                               (winner[0], highest_bid[0], item_id))
                conn.commit()
                flash('Auction ended! Item sold to the winner.', 'success')
            else:
                flash('No bids were placed for this item.', 'warning')
        else:
            flash('No bids were placed for this item.', 'warning')
    
    return redirect('/profile')

# Logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    flash('Logged out successfully.', 'success')
    return redirect('/')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use Render's port or fallback to 5000
    app.run(host="0.0.0.0", port=port, debug=True)

