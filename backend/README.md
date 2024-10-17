# Backend

This is the backend component of the project, built with FastAPI.

## Structure
```
backend/
│
├── app/
│   ├── main.py            # Entry point of our FastAPI app
│   ├── auth.py            # authentication setup 
│   ├── db.py              # Database connection setup 
│   ├── models/            # Pydantic models for request and response bodies
│   │   ├── home.py
│   │   ├── login.py
│   │   ├── report.py
│   │   └── upload.py
│   └── routes/            # API routes
│       ├── home_routes.py
│       ├── login_routes.py
│       ├── report_routes.py
│       └── upload_routes.py
│
├── requirements.txt       # Python dependencies
└── README.md              # Project documentation
```

## Examples

1. **Models**: Contains models for request and response bodies.
    ```python
    class LoginData(BaseModel):
    email: str
    password: str
    ```
2. **Routes**: Contains API routes. 
    ```python
    @router.post("/login")
    async def login(data: LoginData):
        if data.email == "user" and data.password == "password":
            print("Login successful")
            return {"message": "Login successful", "token": "token"}
        else:
            raise HTTPException(status_code=400, detail="Invalid credentials")
    ```
3. **db.py**: Contains the database connection setup.

4. **auth.py**: Contains authentication setup.

## Authentication Flow: Frontend to Backend Integration for User Login

1.	**User Input and Frontend Initiation**
    ```javascript
    const response = await apiClient.login({
            email: username.value,
            password: password.value
        });
    ```
* The frontend initiates the login process upon user submission, invoking the `apiClient.login` method with the provided credentials.

2.	**API Request to Backend**
    ```javascript
    const response = await axios.post("http://localhost:8000/login", {
        email: data.email,
        password: data.password
    });
    ```
* An HTTP POST request is sent to the backend endpoint using Axios, transmitting the user's email and password for authentication.

3.	**Backend Authentication Proces**
    ```python
    @router.post("/login")
    async def login(data: LoginData):
        if data.email == "user" and data.password == "password":
            print("Login successful")
            return {"message": "Login successful", "token": "token"}
        else:
            raise HTTPException(status_code=400, detail="Invalid credentials")
    ```
* The backend, implemented with FastAPI, processes the login request. It validates the credentials against predefined values (temporary solution until database integration). Upon successful authentication, it returns a success message and a token. For invalid credentials, it raises an HTTP exception.

4.	**Frontend Response Handling**
    ```javascript
    if (response.data.message === "Login successful") {
        console.log("Login successful");
        // Redirect to the home page
    } else {
        console.log("Invalid credentials");
        // Show an error message
    }
    ```
* The frontend evaluates the backend response. For successful authentication, it logs the user in and redirects to the home page. In case of failure, it displays an appropriate error message.

This authentication flow serves as a template for other pages and functionalities within the application, following a similar request-response pattern between the frontend and backend.

## Usage
(Note: This runs the backend without the frontend)

**Start the backend server**:
```
uvicorn app.main:app --reload
```

## Testing
To initiate the tests, run the following command:
```
pytest
```
This will run the tests in the `tests` directory.

The testcases mock the database and test the API endpoints.

## API Documentation

Once the application is running, you can access the interactive API documentation:

* Swagger UI: `http://localhost:8000/docs`
* ReDoc: `http://localhost:8000/redoc`

## Database

This project uses MongoDB. Ensure you have the databases set up and running.
