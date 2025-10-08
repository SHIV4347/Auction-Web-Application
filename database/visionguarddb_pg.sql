-- ---------------------------------------
-- VisionGuardDB PostgreSQL Schema
-- ---------------------------------------

-- Users table
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    mobile_number VARCHAR(15) NOT NULL,
    address VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Items table
CREATE TABLE items (
    item_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id),
    item_name VARCHAR(100) NOT NULL,
    age INT NOT NULL,
    description VARCHAR(255) NOT NULL,
    starting_price NUMERIC(18,2) NOT NULL,
    image_path VARCHAR(255) NOT NULL,
    auction_ended BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    sold_price NUMERIC(18,2),
    sold_to INT
);

-- Bids table
CREATE TABLE bids (
    bid_id SERIAL PRIMARY KEY,
    item_id INT NOT NULL REFERENCES items(item_id),
    user_id INT NOT NULL REFERENCES users(user_id),
    bid_amount NUMERIC(18,2) NOT NULL,
    bid_time TIMESTAMP DEFAULT NOW()
);

-- Owners table
CREATE TABLE owners (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    age INT NOT NULL,
    chat_id VARCHAR(100) NOT NULL,
    image_path VARCHAR(255) NOT NULL
);
