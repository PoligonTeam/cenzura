# Functions
Functions are declared using the fn keyword. You can implicitly return an object without the return keyword
```lua
fn add(a, b) { a + b }
add(1, 2)
```
```lua
fn Vec(x, y, z) {
    {
        borrow(x, y, z);

        x = &x;
        y = &y;
        z = &z;
    }
}

Vec(1, 2, 3)
```