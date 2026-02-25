from AU2.plugins.util.render_utils import adjust_brightness


class TestRenderUtils:
    def test_adjust_brightness(self):
        assert adjust_brightness("#a7b231", 1).lower() == "#a7b231"
        assert adjust_brightness("#64091b", 0).lower() == "#000000"
        assert adjust_brightness("#c9d1c4", -10).lower() == "#000000"
        assert adjust_brightness("#a81245", 255).lower() == "#ffffff"
        assert adjust_brightness("#15a28b", 0.5).lower() == "#0a5145"
        assert adjust_brightness("#88bc0f", 1/3).lower() == "#2d3e05"
