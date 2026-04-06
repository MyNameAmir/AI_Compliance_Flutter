# AI_Compliance_Flutter

To run this program, you need to set the environment variables for the following:

OPENAI_API_KEY
MYSQL_HOST
MYSQL_PORT
MYSQL_USER
MYSQL_PASS
MYSQL_DB

Make sure the table to store the data follows the correct data types such as the following

 CREATE TABLE IF NOT EXISTS violations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            person_id VARCHAR(255),
            person_role VARCHAR(255),
            incident_file VARCHAR(255),
            decision VARCHAR(255) NOT NULL,
            violation_result_text TEXT,
            severity VARCHAR(255),
            severity_reason TEXT,
            sanction_level VARCHAR(255),
            recommended_action TEXT,
            sanction_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );


The program runs on Flutter for the front end so ensure you have installed following this page

https://docs.flutter.dev/install/quick

To run the flutter front end you need to cd into frontend and run "flutter run -d chrome"

to run the backend you need to cd into backend and run "uvicorn app:app --reload --port 8002"

ensure you are on the 8002 and port.

Any questions email amiralimoin@cmail.carleton.ca or fshok080@uottawa.ca
