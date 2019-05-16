<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "sentences" %>

<%def name="sidebar()">
    <%util:well title="Dictionary">
        <% dictionary = ctx.dictionary %>
        ${h.link(request, dictionary)} by ${h.linked_contributors(request, dictionary)}
        ${h.button('cite', onclick=h.JSModal.show(dictionary.name, request.resource_url(dictionary, ext='md.html')))}
    </%util:well>
</%def>

<h2>${ctx.dictionary.name}: ${_('Sentence')} ${ctx.number}</h2>
<h4>Word senses:</h4>
<ul>
    % for wa in ctx.meaning_assocs:
        <li>
            <span class="lemma">${wa.meaning.word.name}</span>
            &nbsp;
            <span class="translation">${h.link(request, wa.meaning.word, label=wa.meaning.name)}</span>
        </li>
    % endfor
</ul>

${h.rendered_sentence(ctx)|n}
% if ctx.alt_translation1:
    <div class="alt_translation">
        <span class="translation alt-translation alt-translation1">${ctx.alt_translation1}</span>
        <span class="alt-translation1">[${ctx.alt_translation_language1}]</span>
    </div>
% endif
% if ctx.alt_translation2:
    <div class="alt_translation">
        <span class="translation alt-translation alt-translation2">${ctx.alt_translation2}</span>
        <span class="alt-translation2">[${ctx.alt_translation_language2}]</span>
    </div>
% endif

% if getattr(ctx, 'audio'):
<div style="margin-top: 20px;">
    ${u.cdstar.audio(ctx.audio)}
</div>
% endif

<dl>
% if ctx.comment:
<dt>Comment:</dt>
<dd>${ctx.markup_comment or ctx.comment|n}</dd>
% endif
% if ctx.type:
<dt>${_('Type')}:</dt>
<dd>${ctx.type}</dd>
% endif
% if ctx.references or ctx.source:
<dt>${_('Source')}:</dt>
% if ctx.source:
<dd><span class="muted">${ctx.source}</span></dd>
% endif
% if ctx.references:
<dd>${h.linked_references(request, ctx)|n}</dd>
% endif
% endif
</dl>
