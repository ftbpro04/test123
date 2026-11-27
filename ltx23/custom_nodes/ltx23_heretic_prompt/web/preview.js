import { app } from "../../../scripts/app.js";
import { ComfyWidgets } from "../../../scripts/widgets.js";
app.registerExtension({
  name: "ltx23.heretic.prompt.preview",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "LTX23HereticPrompt") return;
    const previous = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function(message) {
      previous?.apply(this, arguments);
      let widget = this.widgets?.find(w => w.name === "generated_prompt_preview");
      if (!widget) {
        widget = ComfyWidgets.STRING(this, "generated_prompt_preview", ["STRING", {multiline: true}], app).widget;
        widget.options.serialize = false;
        this.setSize([Math.max(this.size[0], 600), Math.max(this.size[1], 780)]);
      }
      widget.value = (message.text || []).join("\n");
      if (widget.inputEl) widget.inputEl.readOnly = true;
      this.setDirtyCanvas(true, true);
    };
  }
});
