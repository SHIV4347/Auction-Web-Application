-- Create Users table
CREATE TABLE Users (
    user_id INT PRIMARY KEY IDENTITY(1,1),
    name NVARCHAR(100) NOT NULL,
    email NVARCHAR(100) NOT NULL UNIQUE,
    mobile_number NVARCHAR(15) NOT NULL,
    address NVARCHAR(255) NOT NULL,
    password NVARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT GETDATE()
);

-- Create Items table
CREATE TABLE Items (
    item_id INT PRIMARY KEY IDENTITY(1,1),
    user_id INT NOT NULL,
    item_name NVARCHAR(100) NOT NULL,
    age INT NOT NULL,
    description NVARCHAR(255) NOT NULL,
    starting_price DECIMAL(18, 2) NOT NULL,
    image_path NVARCHAR(255) NOT NULL,
    auction_ended BIT DEFAULT 0,
    created_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- Create Bids table
CREATE TABLE Bids (
    bid_id INT PRIMARY KEY IDENTITY(1,1),
    item_id INT NOT NULL,
    user_id INT NOT NULL,
    bid_amount DECIMAL(18, 2) NOT NULL,
    bid_time DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (item_id) REFERENCES Items(item_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

ALTER TABLE Items ADD sold_price DECIMAL(18, 2) NULL;
ALTER TABLE Items ADD sold_to INT NULL;

delete from Users where
name = 'SHIVPRASAD SATISH MALI';


select * from Items
select * from Users
select * from Bids



