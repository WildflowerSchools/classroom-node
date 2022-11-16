import click

from capture import upload_loop, capture_loop


@click.command()
@click.option('-a', '--action', help='action to take', required=True)
def main(action):
    if action=="upload":
        upload_loop()
    if action=="capture":
        capture_loop()


if __name__ == '__main__':
    main()  # pylint: disable=E1120
