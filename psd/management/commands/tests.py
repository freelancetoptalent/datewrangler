from django_docopt_command import DocOptCommand


class Command(DocOptCommand):
    # This usage string defines the command options:
    docs = "Usage: command <option1> <option2> [--flag1]"

    def handle_docopt(self, arguments):
        print(arguments)
