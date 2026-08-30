# Common API response format

All auth APIs (and the rest of the project) use this shape:

```json
{
  "status": "success",
  "message": "Signup successful",
  "details": "",
  "data": {}
}
```

| Field | Meaning |
|-------|---------|
| `status` | `"success"` or `"fail"` |
| `message` | Simple string for UI (toast / alert) |
| `details` | Extra error detail as a simple string (often same as `message`) |
| `data` | Payload on success (`null` or omit content on fail) |

### Success example

```json
{
  "status": "success",
  "message": "Login successful",
  "details": "",
  "data": {
    "tokens": { "access": "...", "refresh": "..." },
    "user": { }
  }
}
```

### Fail example

```json
{
  "status": "fail",
  "message": "A user with this phone already exists.",
  "details": "A user with this phone already exists.",
  "data": null
}
```
