{{#empty}}
[+] No {{noun}} found.
{{/empty}}
{{^empty}}
{{green}}[+] {{Noun}} found:{{endc}}
{{/empty}}
{{#items}}
    {{name}} {{blue}}{{url}}{{endc}}
    {{#imu}}
        {{blue}}{{url}}{{endc}}
    {{/imu}}
{{/items}}
