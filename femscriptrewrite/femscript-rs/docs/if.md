# If statements
If statements consist of two or three blocks
If the first block returns true, the second block starts executing, if not, the third (if it exists)
```lua
if { 2 > 1 } {
    "two is greater than one"
}
```
```lua
if { 2 < 1 } {
    Error("how is this even possible!?")
} else {
    "one is NOT greater than two"
}
```
```lua
if {
    resp = await(request("GET", url));
    resp.status == 404
} {
    "nah, doesn't exists"
} else {
    "hell yeah"
}
```