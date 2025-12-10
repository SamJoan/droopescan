
from todo.main import TodoTest

def test_todo(tmp):
    with TodoTest() as app:
        res = app.run()
        print(res)
        raise Exception

def test_command1(tmp):
    argv = ['command1']
    with TodoTest(argv=argv) as app:
        app.run()
