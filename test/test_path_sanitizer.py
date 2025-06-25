from holunder.path_sanitizer import default_sanitize_path


def test_default_sanitize_path():
    assert default_sanitize_path('w&ird ch@ractèrs...') == 'wird_chracters'
    assert default_sanitize_path('normal_filename.md') == 'normal_filename.md'
