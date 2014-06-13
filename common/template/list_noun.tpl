{{#empty}}
{{fail}}[+] No {{noun}} found.{{endc}}
{{/empty}}
{{^empty}}
{{blue}}[+] {{Noun}} found:{{endc}}
{{/empty}}
{{#items}}
    {{name}} {{url}}
{{/items}}
