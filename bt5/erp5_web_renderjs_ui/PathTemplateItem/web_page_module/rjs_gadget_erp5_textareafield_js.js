/*global window, rJS */
/*jslint indent: 2, maxerr: 3 */
(function (window, rJS) {
  "use strict";

  rJS(window)
    .setState({
      tag: 'pre'
    })
    .declareMethod('render', function (options) {
      var field_json = options.field_json || {},
        state_dict = {
          value: field_json.value || field_json.default || "",
          editable: field_json.editable,
          name: field_json.key,
          id: field_json.key,
          error_text: field_json.error_text,
          title: field_json.description,
          hidden: field_json.hidden,
          required: field_json.required,
          // Force calling subfield render
          // as user may have modified the input value
          render_timestamp: new Date().getTime()
        };
      state_dict.text_content = state_dict.value;
      return this.changeState(state_dict);
    })

    .onStateChange(function (modification_dict) {
      var element = this.element,
        gadget = this,
        url,
        result;

      if (modification_dict.hasOwnProperty('editable')) {
        if (gadget.state.editable) {
          url = 'gadget_html5_textarea.html';
        } else {
          url = 'gadget_html5_element.html';
        }
        result = this.declareGadget(url, {scope: 'sub'})
          .push(function (input) {
            // Clear first to DOM, append after to reduce flickering/manip
            while (element.firstChild) {
              element.removeChild(element.firstChild);
            }
            element.appendChild(input.element);
            return input;
          });
      } else {
        result = this.getDeclaredGadget('sub');
      }
      return result
        .push(function (input) {
          return input.render(gadget.state);
        });
    })

    .declareMethod('checkValidity', function () {
      return this.getDeclaredGadget('sub')
        .push(function (subgadget) {
          return subgadget.checkValidity();
        });
    }, {mutex: 'changestate'})

    .declareMethod('getContent', function () {
      if (this.state.editable) {
        return this.getDeclaredGadget('sub')
          .push(function (gadget) {
            return gadget.getContent();
          });
      }
      return {};
    }, {mutex: 'changestate'});

}(window, rJS));