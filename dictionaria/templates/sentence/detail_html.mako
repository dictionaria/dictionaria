<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%! active_menu_item = "sentences" %>

<%def name="sidebar()">
    <%util:well title="Dictionary">
        <% dictionary = ctx.meaning_assocs[0].meaning.word.dictionary %>
        ${h.link(request, dictionary)} by ${h.linked_contributors(request, dictionary)}
        ${h.button('cite', onclick=h.JSModal.show(dictionary.name, request.resource_url(dictionary, ext='md.html')))}
    </%util:well>
</%def>

<h2>${_('Sentence')} ${ctx.id}</h2>
<dl>
    <dt>Language:</dt>
    <dd>${h.link(request, ctx.language)}</dd>
    <dt>Meanings:</dt>
    <dd>
        <ul>
            % for wa in ctx.meaning_assocs:
                <li>
                    ${h.link(request, wa.meaning.word, label=wa.meaning.name)}
                    [${wa.meaning.word.name}]
                </li>
            % endfor
        </ul>
    </dd>
</dl>

${h.rendered_sentence(ctx)|n}
% if ctx.alt_translation:
    <div style="margin-top: -10px;">
        <span class="translation">${ctx.alt_translation}</span>
        <span>[${ctx.alt_translation_language}]</span>
    </div>
% endif
% if ctx.alt_translation2:
    <div style="margin-top: -10px;">
        <span class="translation">${ctx.alt_translation2}</span>
        <span>[${ctx.alt_translation_language2}]</span>
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
<dd>${ctx.source}</dd>
% endif
% if ctx.references:
<dd>${h.linked_references(request, ctx)|n}</dd>
% endif
% endif
</dl>