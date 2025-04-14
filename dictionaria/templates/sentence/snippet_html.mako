<%inherit file="../snippet.mako"/>
<%namespace name="util" file="../util.mako"/>

${h.rendered_sentence(ctx)}
% if ctx.alt_translation1:
<div class="alt_translation">
  <span class="alt-translation alt-translation1 translation">${ctx.alt_translation1}</span>
  <span class="alt-translation alt-translation1">[${ctx.alt_translation_language1}]</span>
</div>
% endif
% if ctx.alt_translation2:
<div class="alt_translation">
  <span class="alt-translation alt-translation2 translation">${ctx.alt_translation2}</span>
  <span class="alt-translation alt-translation2">[${ctx.alt_translation_language2}]</span>
</div>
% endif
