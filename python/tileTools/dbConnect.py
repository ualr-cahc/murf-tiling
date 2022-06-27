import mysql.connector

def dbConnect(password, database):
    """connects to localhost database with user set to 'python'"""
    
    db = mysql.connector.connect(
        host='localhost',
        user="python",
        password=password,
        database=database
    )
    return db
