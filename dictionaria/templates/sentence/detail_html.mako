<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%namespace name="dutil" file="../dutil.mako"/>
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
            <span class="translation">${h.link(request, wa.meaning.word, label=u.drop_unit_links(wa.meaning.name))}</span>
        </li>
    % endfor
</ul>

${dutil.sentence(ctx)}
