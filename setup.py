try:
    from setuptools import setup, Extension
except ImportError:
    from distutils.core import setup, Extension


description = """
Timyd - Timyd Is Monitoring Your Domain!
"""
setup(name='Timyd',
      version='0.0',
      packages=['timyd'],
      entry_points={
        'console_scripts': [
          'timyd = timyd.run:main']}
      description='A network monitoring/spying software',
      author="Remi Rampin",
      author_email='remirampin@gmail.com',
      url='http://github.com/remram44/timyd',
      long_description=description,
      license='MIT',
      classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "License :: OSI Approved :: MIT License",
        'Programming Language :: Python'])
