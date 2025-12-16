<%inherit file="../${context.get('request').registry.settings.get('clld.app_template', 'app.mako')}"/>
<%namespace name="util" file="../util.mako"/>
<%namespace name="dutil" file="../dutil.mako"/>
<%! active_menu_item = "units" %>

<%def name="sidebar()">
    <%util:well title="Dictionary">
        ${h.link(request, ctx.dictionary)} by ${h.linked_contributors(request, ctx.dictionary)}
        ${h.button('cite', onclick=h.JSModal.show(ctx.dictionary.name, request.resource_url(ctx.dictionary, ext='md.html')))}
    </%util:well>
    % for file in ctx._files:
        % if file.mime_type.startswith('audio'):
            <p>
                ${u.cdstar.audio(file)}
            </p>
        % endif
    % endfor
    % for file in ctx.iterfiles():
        % if file.mime_type.startswith('image'):
            <div class="img-with-caption well">
                ${u.cdstar.linked_image(file)}
                % if file.jsondata.get('description'):
                <p>${file.jsondata.get('description')}</p>
                % endif
            </div>
        % endif
    % endfor
</%def>

<h2>${ctx.label} <span class="meanings-in-title">${u.add_word_links(req, ctx.dictionary, u.truncate(' / '.join(u.split(m.name)[0] for m in ctx.meanings)))|n}</span></h2>

${dutil.word_details()}
