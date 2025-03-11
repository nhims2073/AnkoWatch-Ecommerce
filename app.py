from flask import Flask
import routes

app = routes.app

if __name__ == '__main__':
    app.run(debug=True)