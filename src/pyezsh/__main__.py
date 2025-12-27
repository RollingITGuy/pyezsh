from pyezsh.app import App
from pyezsh.ui import Component


def build_app(app: App) -> None:
	"""
	Compose the initial UI tree.

	This function is intentionally small and declarative.
	"""
	# Example placeholder:
	# app.add_component(SomeComponent())
	pass


def main() -> None:
	app = App()
	build_app(app)
	app.run()


if __name__ == "__main__":
	main()
