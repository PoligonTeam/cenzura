# Syntax
Some code examples for better understanding of the syntax
```lua
response = await(request("GET", "https://cenzura-api.poligon.lgbt/"));
data = response.json;

embed = Embed{color=randint(0, hex("ffffff"))};
embed.set_thumbnail{borrow(data); url=format("https://cdn.discordapp.com/avatars/{}/{}.png", &data.id, &data.avatar)};
embed.add_field{borrow(data); name="id:"; value=&data.id};
embed.add_field{borrow(data); name="username:"; value=&data.username};

return embed;
```
You can implicitly return an object without the return keyword
```lua
embed = Embed();
embed
```
```lua
"Hello world!"
```

# Args and kwargs
Arguments are simply lists and kwargs are scopes. You use them when you call a function to pass everything what's needed
- Args
    ```lua
    request(method, url);
    ```
- Kwargs
    ```lua
    request{method=method; url=url};
    ```