from flask import Flask, render_template, request, redirect, session, flash
import pyodbc
import os
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database connection
def get_db_connection():
    conn = pyodbc.connect('Driver={SQL Server};'
                          'Server=SHIVPRASAD\\SQLEXPRESS;'
                          'Database=master;'
                          'Trusted_Connection=yes;')
    return conn


@app.route('/')
def home():
    items = []
    bids = {}
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Query to get all items with their highest bid and highest bidder details
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
           FROM Items i
           JOIN Users u ON i.user_id = u.user_id
           LEFT JOIN (
               SELECT 
                   item_id, 
                   MAX(bid_amount) AS highest_bid 
               FROM Bids 
               GROUP BY item_id
           ) AS highest_bid_data ON i.item_id = highest_bid_data.item_id
           LEFT JOIN Bids b ON highest_bid_data.item_id = b.item_id AND highest_bid_data.highest_bid = b.bid_amount
           LEFT JOIN Users ub ON b.user_id = ub.user_id
           WHERE i.auction_ended = 0  -- Exclude sold items
        ''')

        items = cursor.fetchall()
        
        # Query to get all bids for each item
        cursor.execute('''
            SELECT b.item_id, b.bid_amount, u.name AS bidder_name
            FROM Bids b
            JOIN Users u ON b.user_id = u.user_id
            ORDER BY b.item_id, b.bid_amount DESC
        ''')
        all_bids = cursor.fetchall()
        
        # Organize bids by item_id for easy access in the template
        for bid in all_bids:
            item_id = bid[0]  # Access item_id by index
            if item_id not in bids:
                bids[item_id] = []
            bids[item_id].append({
                'bid_amount': bid[1],  # Access bid_amount by index
                'bidder_name': bid[2]  # Use this as the name of the bidder
            })
    
    return render_template('home.html', items=items, bids=bids)


# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password))
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

# Registration Page
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
            cursor.execute('INSERT INTO users (name, email, mobile_number, address, password) VALUES (?, ?, ?, ?, ?)',
                           (name, email, mobile_number, address, password))
            conn.commit()
            flash('Registered successfully! Please log in.', 'success')
            return redirect('/login')
    return render_template('registration.html')


# Set the upload folder
UPLOAD_FOLDER = 'static/images'  # Specify your upload folder path
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}  # Allowed file extensions

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/profile')
def profile():
    if 'email' not in session:
        return redirect('/login')

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (session['email'],))
        user = cursor.fetchone()

        if user is None:
            return redirect('/login')

        # Fetch user items including sold price and winner's name
        cursor.execute('''
           SELECT i.item_id, i.item_name, i.starting_price, i.sold_price, u.name AS winner_name
           FROM items i
           LEFT JOIN Users u ON i.sold_to = u.user_id
           WHERE i.user_id = ?
        ''', (user[0],))
        user_items = cursor.fetchall()


        # Fetch user bids
        cursor.execute('SELECT b.bid_amount, i.item_name FROM bids b JOIN items i ON b.item_id = i.item_id WHERE b.user_id = ?', (user[0],))
        user_bids = cursor.fetchall()

        # Fetch won items
        cursor.execute('''
            SELECT i.item_name, i.sold_price 
            FROM items i 
            WHERE i.sold_to = ? AND i.auction_ended = 1
        ''', (user[0],))
        user_wins = cursor.fetchall()

    return render_template('profile.html', user=user, user_items=user_items, user_bids=user_bids, user_wins=user_wins)


# Add Item Page
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
                filename = secure_filename(image.filename)  # Sanitize the filename
                image_path = os.path.join(UPLOAD_FOLDER, filename)  # Store the path
                image.save(image_path)  # Save the file
        
        # Set a default image path if no image is uploaded
        if not image_path:
            image_path = os.path.join(UPLOAD_FOLDER, 'default_image.jpg')  # Replace with your default image name
        
        # Store only the relative path for the image in the database
        relative_image_path = image_path.replace('static/', '').replace('\\', '/')  # Store as 'images/filename.jpg'
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO items (item_name, age, description, starting_price, user_id, image_path) VALUES (?, ?, ?, ?, ?, ?)',
                           (item_name, age, description, starting_price, session['user_id'], relative_image_path))
            conn.commit()
            flash('Item added successfully!', 'success')
            return redirect('/')
    
    return render_template('add_item.html')



# Bid on Item
@app.route('/bid/<int:item_id>', methods=['POST'])
def bid(item_id):
    if 'user_id' not in session:
        return redirect('/login')  # Ensure the user is logged in

    bid_amount = request.form['bid_amount']
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO bids (item_id, user_id, bid_amount) VALUES (?, ?, ?)',
            (item_id, session['user_id'], bid_amount)
        )
        conn.commit()
        flash('Bid placed successfully!', 'success')
    
    return redirect('/')

@app.route('/end_auction/<int:item_id>', methods=['POST'])
def end_auction(item_id):
    if 'user_id' not in session:
        return redirect('/login')
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Find the highest bid for the item
        cursor.execute('SELECT MAX(bid_amount) AS max_bid FROM bids WHERE item_id = ?', (item_id,))
        highest_bid = cursor.fetchone()
        
        if highest_bid and highest_bid[0]:  # Accessing the max_bid with index
            # Find the user who made the highest bid
            cursor.execute('SELECT user_id FROM bids WHERE item_id = ? AND bid_amount = ?', (item_id, highest_bid[0]))
            winner = cursor.fetchone()
            
            # Mark the item as sold, update its owner, and set auction_ended
            if winner:
                cursor.execute(''' 
                    UPDATE items 
                    SET sold_to = ?, sold_price = ?, auction_ended = 1 
                    WHERE item_id = ?''', 
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

if __name__ == '__main__':
    app.run(debug=True)