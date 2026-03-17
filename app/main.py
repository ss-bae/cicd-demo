from flask import Flask, jsonify, request

app = Flask(__name__)

items = []


@app.route("/")
def index():
    return jsonify({"message": "Hello, World!", "status": "ok"})


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


@app.route("/items", methods=["GET"])
def get_items():
    return jsonify({"items": items})


@app.route("/items", methods=["POST"])
def add_item():
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "name is required"}), 400
    item = {"id": len(items) + 1, "name": data["name"]}
    items.append(item)
    return jsonify(item), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
