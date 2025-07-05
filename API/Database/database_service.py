import pymssql
import os
import dotenv
import json
from datetime import datetime
from decimal import Decimal

# Load environment variables
dotenv.load_dotenv()

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

# def get_connection():
#     """
#     Establish and return a connection to the PostgreSQL database
    
#     Returns:
#         connection: A PostgreSQL database connection
#     """
#     try:
#         conn = psycopg2.connect(
#             host=os.getenv("POSTGRES_HOST"),
#             database=os.getenv("POSTGRES_DB"),
#             user=os.getenv("POSTGRES_USER"),
#             password=os.getenv("POSTGRES_PASSWORD"),
#             port=os.getenv("POSTGRES_PORT")
#         )
#         return conn
#     except Exception as e:
#         print(f"Error connecting to the database: {str(e)}")
#         return None

def get_connection():
    """
    Thiết lập và trả về một kết nối tới database SQL Server bằng pymssql.

    Returns:
        connection: Một đối tượng kết nối database của pymssql, hoặc None nếu kết nối thất bại.
    """
    try:
        # Bỏ hoàn toàn việc tạo connection_string.
        # Thay vào đó, truyền thẳng các thông tin vào hàm pymssql.connect()
        # dưới dạng các tham số được đặt tên (keyword arguments).
        conn = pymssql.connect(
            server=os.getenv('SQLSERVER_HOST'),
            user=os.getenv('SQLSERVER_USER'),
            password=os.getenv('SQLSERVER_PASSWORD'),
            database=os.getenv('SQLSERVER_DB'),
            port=os.getenv('SQLSERVER_PORT', 1433) # Thêm port và đặt giá trị mặc định
        )
        
        print(">>>>> Da ket noi thanh cong toi SQL Server bang pymssql. <<<<<")
        return conn

    except Exception as e:
        print(f">>>>> Loi khi ket noi voi pymssql: {e} <<<<<")
        return None

def execute_query(query, params=None, fetch=True):
    """
    Execute a SQL query and fetch results if needed
    
    Args:
        query (str): SQL query to execute
        params (tuple or dict): Parameters for the query
        fetch (bool): Whether to fetch and return results
    
    Returns:
        list: Query results if fetch is True, else None
    """
    conn = get_connection()
    if not conn:
        return None
        
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                if fetch:
                    return cur.fetchall()
                return None
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        return None
    finally:
        conn.close()

def insert_data(table, data):
    """
    Insert data into a table
    
    Args:
        table (str): Name of the table
        data (dict): Data to insert {column: value}
    
    Returns:
        int: ID of inserted row if successful, None otherwise
    """
    columns = list(data.keys())
    values = list(data.values())
    placeholders = [f"%({key})s" for key in columns]
    
    query = f"""
    INSERT INTO {table} ({', '.join(columns)})
    VALUES ({', '.join(placeholders)})
    RETURNING id
    """
    
    conn = get_connection()
    if not conn:
        return None
        
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(query, data)
                return cur.fetchone()[0]
    except Exception as e:
        print(f"Error inserting data: {str(e)}")
        return None
    finally:
        conn.close()

def update_data(table, data, condition):
    """
    Update data in a table
    
    Args:
        table (str): Name of the table
        data (dict): Data to update {column: value}
        condition (str): WHERE condition
    
    Returns:
        bool: True if successful, False otherwise
    """
    set_clause = ", ".join([f"{key} = %({key})s" for key in data.keys()])
    
    query = f"""
    UPDATE {table}
    SET {set_clause}
    WHERE {condition}
    """
    
    conn = get_connection()
    if not conn:
        return False
        
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(query, data)
                return True
    except Exception as e:
        print(f"Error updating data: {str(e)}")
        return False
    finally:
        conn.close()

def delete_data(table, condition):
    """
    Delete data from a table
    
    Args:
        table (str): Name of the table
        condition (str): WHERE condition
    
    Returns:
        bool: True if successful, False otherwise
    """
    query = f"""
    DELETE FROM {table}
    WHERE {condition}
    """
    
    conn = get_connection()
    if not conn:
        return False
        
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(query)
                return True
    except Exception as e:
        print(f"Error deleting data: {str(e)}")
        return False
    finally:
        conn.close()

def get_version():
    """
    Get database version for testing connection
    
    Returns:
        str: Database version if successful, None otherwise
    """
    query = "SELECT VERSION()"
    result = execute_query(query)
    
    if result and len(result) > 0:
        return result[0]["version"]
    return None

def get_all_data(table_name):
    """
    Retrieve all data from a specified table
    
    Args:
        table_name (str): Name of the table to query
        
    Returns:
        list: List of dictionaries containing all rows from the table
    """
    query = f"SELECT * FROM {table_name}"
    try:
        conn = get_connection()
        if not conn:
            return {"error": "Failed to connect to database"}
            
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            results = cur.fetchall()
            return results
    except Exception as e:
        return {"error": f"Error retrieving data: {str(e)}"}
    finally:
        if conn:
            conn.close()

def get_database_name():
    """
    Get the database name from environment variables
    
    Returns:
        str: Database name
    """
    return os.getenv("POSTGRES_DB", "defaultdb")

# def getConnectionString():
#     """
#     Get the PostgreSQL connection string using environment variables
    
#     Returns:
#         str: PostgreSQL connection string in format postgresql://username:password@host:port/database
#     """
#     host = os.getenv("POSTGRES_HOST")
#     port = os.getenv("POSTGRES_PORT")
#     user = os.getenv("POSTGRES_USER")
#     password = os.getenv("POSTGRES_PASSWORD")
#     db = os.getenv("POSTGRES_DB")
    
#     return f"postgresql://{user}:{password}@{host}:{port}/{db}"

def getConnectionString():
    """
    Get the SQL Server connection string using environment variables

    Returns:
        str: SQL Server connection string
    """
    host = os.getenv("SQLSERVER_HOST")
    port = os.getenv("SQLSERVER_PORT")
    user = os.getenv("SQLSERVER_USER")
    password = os.getenv("SQLSERVER_PASSWORD")
    db = os.getenv("SQLSERVER_DB")

    # Construct the connection string for SQL Server
    # Note: Ensure the ODBC Driver is installed on your system.
    # Common driver is "ODBC Driver 17 for SQL Server"
    connection_string = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={host},{port};"
        f"DATABASE={db};"
        f"UID={user};"
        f"PWD={password}"
    )
    return connection_string

# def create_tables():
#     """
#     Create the necessary database tables if they don't exist
    
#     This function creates all required tables for the application with proper
#     indexes and constraints. It's designed to be idempotent and safe to run
#     in production environments.
    
#     Returns:
#         bool: True if successful, False otherwise
#     """
#     conn = get_connection()
#     if not conn:
#         print("Failed to connect to the database")
#         return False
    
#     try:
#         with conn.cursor() as cur:
#             # Check if tables already exist
#             cur.execute("""
#                 SELECT table_name 
#                 FROM information_schema.tables 
#                 WHERE table_schema = 'public' 
#                 AND table_name IN ('users', 'users_image', 'clothes', 'tryOnImage', 'feedback')
#             """)
#             existing_tables = [row[0] for row in cur.fetchall()]
            
#             if existing_tables:
#                 print(f"Found existing tables: {', '.join(existing_tables)}")
#                 print("Tables will be created only if they don't exist")
            
#             # Create users table
#             cur.execute("""
#                 CREATE TABLE IF NOT EXISTS users (
#                     id SERIAL PRIMARY KEY,
#                     username VARCHAR(100) UNIQUE NOT NULL,
#                     email VARCHAR(255) UNIQUE NOT NULL,
#                     password_hash VARCHAR(255) NOT NULL,
#                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                 )
#             """)
            
#             # Create index on username and email for faster lookups
#             cur.execute("""
#                 CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)
#             """)
#             cur.execute("""
#                 CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
#             """)
            
#             # Create users_image table
#             cur.execute("""
#                 CREATE TABLE IF NOT EXISTS users_image (
#                     id SERIAL PRIMARY KEY,
#                     user_id INTEGER REFERENCES users(id) NULL,
#                     public_id VARCHAR(255) NOT NULL,
#                     url TEXT NOT NULL,
#                     upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                 )
#             """)
            
#             # Create indexes for users_image
#             cur.execute("""
#                 CREATE INDEX IF NOT EXISTS idx_users_image_user_id ON users_image(user_id)
#             """)
#             cur.execute("""
#                 CREATE INDEX IF NOT EXISTS idx_users_image_public_id ON users_image(public_id)
#             """)
            
#             # Create clothes table
#             cur.execute("""
#                 CREATE TABLE IF NOT EXISTS clothes (
#                     id SERIAL PRIMARY KEY,
#                     user_id INTEGER REFERENCES users(id) NULL,
#                     public_id VARCHAR(255) NOT NULL,
#                     url TEXT NOT NULL,
#                     upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                 )
#             """)
            
#             # Create indexes for clothes
#             cur.execute("""
#                 CREATE INDEX IF NOT EXISTS idx_clothes_user_id ON clothes(user_id)
#             """)
#             cur.execute("""
#                 CREATE INDEX IF NOT EXISTS idx_clothes_public_id ON clothes(public_id)
#             """)
            
#             # Create tryOnImage table
#             cur.execute("""
#                 CREATE TABLE IF NOT EXISTS tryOnImage (
#                     id SERIAL PRIMARY KEY,
#                     user_id INTEGER REFERENCES users(id) NULL,
#                     user_image_id INTEGER REFERENCES users_image(id),
#                     clothes_id INTEGER REFERENCES clothes(id),
#                     public_id VARCHAR(255) NOT NULL,
#                     url TEXT NOT NULL,
#                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                 )
#             """)
            
#             # Create indexes for tryOnImage
#             cur.execute("""
#                 CREATE INDEX IF NOT EXISTS idx_tryOnImage_user_id ON tryOnImage(user_id)
#             """)
#             cur.execute("""
#                 CREATE INDEX IF NOT EXISTS idx_tryOnImage_user_image_id ON tryOnImage(user_image_id)
#             """)
#             cur.execute("""
#                 CREATE INDEX IF NOT EXISTS idx_tryOnImage_clothes_id ON tryOnImage(clothes_id)
#             """)
            
#             # Create feedback table
#             cur.execute("""
#                 CREATE TABLE IF NOT EXISTS feedback (
#                     id SERIAL PRIMARY KEY,
#                     tryOnImage_id INTEGER REFERENCES tryOnImage(id),
#                     feedback JSONB NOT NULL,
#                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                 )
#             """)
            
#             # Create index for feedback
#             cur.execute("""
#                 CREATE INDEX IF NOT EXISTS idx_feedback_tryOnImage_id ON feedback(tryOnImage_id)
#             """)
            
#             # Create a schema version table to track migrations
#             cur.execute("""
#                 CREATE TABLE IF NOT EXISTS schema_version (
#                     id SERIAL PRIMARY KEY,
#                     version VARCHAR(50) NOT NULL,
#                     applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                 )
#             """)
            
#             # Check if we need to insert the current version
#             cur.execute("SELECT COUNT(*) FROM schema_version WHERE version = '2.0.0'")
#             if cur.fetchone()[0] == 0:
#                 cur.execute("INSERT INTO schema_version (version) VALUES ('2.0.0')")
            
#             conn.commit()
#             print("Database tables created successfully")
#             return True
#     except Exception as e:
#         print(f"Error creating tables: {str(e)}")
#         conn.rollback()
#         return False
#     finally:
#         conn.close()

def create_tables():
    """
    Tạo các bảng database cần thiết nếu chúng chưa tồn tại trong SQL Server.
    Hàm này được thiết kế để an toàn khi chạy nhiều lần.
    """
    conn = get_connection()
    if not conn:
        print("Failed to connect to the database to create tables.")
        return False

    try:
        # Sử dụng with để đảm bảo cursor được đóng đúng cách
        with conn.cursor() as cur:
            
            # --- Tách mỗi khối IF NOT EXISTS thành một lệnh execute riêng biệt ---

            # Table: users
            print("Checking/Creating table: users...")
            cur.execute("""
                IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[users]') AND type in (N'U'))
                BEGIN
                    CREATE TABLE users (
                        id INT PRIMARY KEY IDENTITY(1,1),
                        username NVARCHAR(100) NOT NULL UNIQUE,
                        email NVARCHAR(255) NOT NULL UNIQUE,
                        password_hash NVARCHAR(255) NOT NULL,
                        created_at DATETIME DEFAULT GETDATE(),
                        last_login DATETIME
                    );
                    CREATE INDEX idx_users_username ON users(username);
                    CREATE INDEX idx_users_email ON users(email);
                END;
            """)
            
            # Table: users_image
            print("Checking/Creating table: users_image...")
            cur.execute("""
                IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[users_image]') AND type in (N'U'))
                BEGIN
                    CREATE TABLE users_image (
                        id INT PRIMARY KEY IDENTITY(1,1),
                        user_id INT REFERENCES users(id) ON DELETE CASCADE, -- Thêm ON DELETE CASCADE
                        public_id NVARCHAR(255) NOT NULL,
                        url NVARCHAR(MAX) NOT NULL,
                        upload_date DATETIME DEFAULT GETDATE()
                    );
                    CREATE INDEX idx_users_image_user_id ON users_image(user_id);
                    CREATE INDEX idx_users_image_public_id ON users_image(public_id);
                END;
            """)

            # Table: clothes
            print("Checking/Creating table: clothes...")
            cur.execute("""
                IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[clothes]') AND type in (N'U'))
                BEGIN
                    CREATE TABLE clothes (
                        id INT PRIMARY KEY IDENTITY(1,1),
                        user_id INT REFERENCES users(id) ON DELETE CASCADE, -- Thêm ON DELETE CASCADE
                        public_id NVARCHAR(255) NOT NULL,
                        url NVARCHAR(MAX) NOT NULL,
                        upload_date DATETIME DEFAULT GETDATE()
                    );
                    CREATE INDEX idx_clothes_user_id ON clothes(user_id);
                    CREATE INDEX idx_clothes_public_id ON clothes(public_id);
                END;
            """)

            # Table: tryOnImage
            print("Checking/Creating table: tryOnImage...")
            cur.execute("""
                IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[tryOnImage]') AND type in (N'U'))
                BEGIN
                    CREATE TABLE tryOnImage (
                        id INT PRIMARY KEY IDENTITY(1,1),
                        user_id INT REFERENCES users(id), -- No cascade here, keep records
                        user_image_id INT REFERENCES users_image(id),
                        clothes_id INT REFERENCES clothes(id),
                        public_id NVARCHAR(255) NOT NULL,
                        url NVARCHAR(MAX) NOT NULL,
                        created_at DATETIME DEFAULT GETDATE()
                    );
                    CREATE INDEX idx_tryOnImage_user_id ON tryOnImage(user_id);
                END;
            """)

            # Table: feedback
            print("Checking/Creating table: feedback...")
            cur.execute("""
                IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[feedback]') AND type in (N'U'))
                BEGIN
                    CREATE TABLE feedback (
                        id INT PRIMARY KEY IDENTITY(1,1),
                        tryOnImage_id INT REFERENCES tryOnImage(id) ON DELETE CASCADE,
                        feedback NVARCHAR(MAX) NOT NULL,
                        created_at DATETIME DEFAULT GETDATE()
                    );
                    CREATE INDEX idx_feedback_tryOnImage_id ON feedback(tryOnImage_id);
                END;
            """)
            
            # Table: schema_version
            print("Checking/Creating table: schema_version...")
            cur.execute("""
                IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[schema_version]') AND type in (N'U'))
                BEGIN
                    CREATE TABLE schema_version (
                        id INT PRIMARY KEY IDENTITY(1,1),
                        version_number NVARCHAR(50) NOT NULL UNIQUE,
                        applied_date DATETIME DEFAULT GETDATE(),
                        description NVARCHAR(MAX)
                    );
                END;
            """)

            # --- Sửa lại logic INSERT và cách kiểm tra ---
            print("Checking/Recording schema version...")
            # Sửa lại cú pháp tham số từ ? sang %s
            version_to_check = '2.0.0'
            description_text = 'Initial schema creation'
            
            cur.execute("SELECT COUNT(*) as count FROM schema_version WHERE version_number = %s", (version_to_check,))
            
            # Sửa lại cách lấy dữ liệu từ row[0] sang row['count'] vì as_dict=True
            if cur.fetchone()[0] == 0:
                cur.execute("INSERT INTO schema_version (version_number, description) VALUES (%s, %s)", (version_to_check, description_text))
                print(f"Schema version '{version_to_check}' recorded.")
            else:
                print(f"Schema version '{version_to_check}' already exists.")

            # Commit tất cả các thay đổi sau khi tất cả các lệnh đã thực thi thành công
            conn.commit()
            print("\nAll database tables checked/created successfully.")
            return True

    except Exception as e:
        print(f"\nAn unexpected error occurred during table creation: {str(e)}")
        # Rollback lại các thay đổi nếu có lỗi xảy ra
        conn.rollback()
        return False
    finally:
        # Luôn luôn đóng kết nối
        if conn:
            conn.close()

def drop_tables():
    """
    Drop all database tables in the correct order to handle dependencies
    
    This function drops tables in reverse order of their creation to handle 
    foreign key constraints properly.
    
    Returns:
        bool: True if successful, False otherwise
    """
    conn = get_connection()
    if not conn:
        print("Failed to connect to the database")
        return False
    
    try:
        with conn.cursor() as cur:
            # Drop tables in order considering foreign key constraints
            
            # First drop feedback table (depends on try_on_results)
            cur.execute("DROP TABLE IF EXISTS feedback CASCADE")
            print("Dropped feedback table")
            
            # Then drop try_on_results table (depends on users and images)
            cur.execute("DROP TABLE IF EXISTS try_on_results CASCADE")
            print("Dropped try_on_results table")
            
            # Then drop images table (has self-references)
            cur.execute("DROP TABLE IF EXISTS images CASCADE")
            print("Dropped images table")
            
            # Finally drop users table
            cur.execute("DROP TABLE IF EXISTS users CASCADE")
            print("Dropped users table")
            
            conn.commit()
            print("All tables dropped successfully")
            return True
    except Exception as e:
        print(f"Error dropping tables: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

# def main():
#     """Test the database connection and data retrieval"""
#     version = get_version()
#     db_name = get_database_name()
#     connection_string = getConnectionString()
    
#     if version:
#         print(f"Connected to PostgreSQL: {version}")
#         print(f"Database name: {db_name}")
#         print(f"Connection string: {connection_string}")
        
#         # Drop tables and recreate them (reset database)
#         print("\nResetting database...")
#         if drop_tables():
#             print("Tables dropped successfully")
#             if create_tables():
#                 print("Tables recreated successfully")
#             else:
#                 print("Failed to recreate tables")
#         else:
#             print("Failed to drop tables")
        
#         # Try to get all data from users table
#         users = get_all_data("users")
#         print("Users data:", users)
#     else:
#         print("Failed to connect to the database")
#         print("\nPlease check your environment variables in .env file:")
#         print(f"POSTGRES_HOST: {os.getenv('POSTGRES_HOST')}")
#         print(f"POSTGRES_DB: {os.getenv('POSTGRES_DB')}")
#         print(f"POSTGRES_USER: {os.getenv('POSTGRES_USER')}")
#         print(f"POSTGRES_PASSWORD: {'*' * len(os.getenv('POSTGRES_PASSWORD', ''))}")
#         print(f"POSTGRES_PORT: {os.getenv('POSTGRES_PORT')}")
#         print(f"Connection string: {connection_string}")

# if __name__ == "__main__":
#     main()

def main():
    """Test the SQL Server database connection"""
    connection_string = getConnectionString()
    conn = get_connection() # Attempt to get a connection

    if conn:
        print(f"Successfully connected to SQL Server.")
        print(f"Connection string: {connection_string}")
        conn.close() # Close the connection when done
        print("Connection closed.")
    else:
        print("Failed to connect to the SQL Server database.")
        print("\nPlease check your environment variables in .env file:")
        print(f"SQLSERVER_HOST: {os.getenv('SQLSERVER_HOST')}")
        print(f"SQLSERVER_DB: {os.getenv('SQLSERVER_DB')}")
        print(f"SQLSERVER_USER: {os.getenv('SQLSERVER_USER')}")
        print(f"SQLSERVER_PASSWORD: {'*' * len(os.getenv('SQLSERVER_PASSWORD', ''))}")
        print(f"SQLSERVER_PORT: {os.getenv('SQLSERVER_PORT')}")
        print(f"Connection string: {connection_string}")

if __name__ == "__main__":
    # For testing purposes, you might want to set dummy environment variables here
    # os.environ['SQLSERVER_HOST'] = 'localhost'
    # os.environ['SQLSERVER_PORT'] = '1433'
    # os.environ['SQLSERVER_DB'] = 'master'
    # os.environ['SQLSERVER_USER'] = 'sa'
    # os.environ['SQLSERVER_PASSWORD'] = 'your_strong_password' # !!! Use your actual password !!!

    main()