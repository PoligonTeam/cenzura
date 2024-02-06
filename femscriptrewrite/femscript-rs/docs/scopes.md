# Scopes
```lua
student = {
    id = 10;
    
    if { id > 69 } {
        form = "2A";
    } else {
        form = "2B";
    }

    person = {
        name = "Joe";
        surname = "Doe";
        sex = "female";
        age = 17;
    };
    formTutor = {
        name = "Grzegorz";
        surname = "Braun";
        sex = "male";
        age = 56;
    };
    classes = [
        "art",
        "photography",
        "edging"
    ];
};

print(format("Hello {} {}", student.person.name, student.person.surname));
print(format("Your id is {}", str(student.id)));
```