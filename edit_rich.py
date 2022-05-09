def make_prompt(DefaultType, Text, style):
  def make_prompt(self, default: DefaultType) -> Text:
    """Make prompt text.
    Args:
        default (DefaultType): Default value.
    Returns:
        Text: Text to display in prompt.
    """
    prompt = self.prompt.copy()
    prompt.end = ""

    if self.show_choices and self.choices:
        _choices = "/".join(self.choices)
        choices = f"[{_choices}]"
        prompt.append(" ")
        prompt.append(choices, style)

    if (
        default != ...
        and self.show_default
        and isinstance(default, (str, self.response_type))
    ):
        prompt.append(" ")
        _default = self.render_default(default)
        prompt.append(_default)

    prompt.append(self.prompt_suffix)

    return prompt
  return make_prompt

def render_default(path, DefaultType, Text, style):
  if path == "Confirm":
    def render_default(self, default: DefaultType) -> Text:
      """Render the default as (y) or (n) rather than True/False."""
      yes, no = self.choices
      return Text(f"({yes})" if default else f"({no})", style=style)
  else: 
    def render_default(self, default: DefaultType) -> Text:
        """Turn the supplied default in to a Text instance.
        Args:
            default (DefaultType): Default value.
        Returns:
            Text: Text containing rendering of default value.
        """
        return Text(f"({default})", style)
  return render_default