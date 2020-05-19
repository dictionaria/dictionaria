<%! from itertools import chain %>


<%def name="data_tr(obj, links=None)">
% for _d in obj.data:
    % if not _d.key.startswith('lang-') and not _d.key.endswith('_links'):
        <tr>
            <td><small>${_d.key.replace('_', ' ')}</small></td>
            <td>
                ## FIXME there must be a better way
                % if _d.key == 'Scientific Name':
                <em>
                % endif
                ${u.add_unit_links(req, ctx.dictionary, _d.value)|n}
                % if _d.key == 'Scientific Name':
                </em>
                % endif
                % if links and _d.key in links:
                    <small>${links[_d.key]|n}</small>
                % endif
                % if _d.key in obj.sourcedict:
                    <ul class="unstyled">
                        % for src in obj.sourcedict[_d.key]:
                            [${h.link(req, src)}]
                        % endfor
                    </ul>
                % endif
            </td>
        </tr>
    % endif
% endfor
</%def>


<%def name="sentence(obj, fmt='long')">
    ${h.rendered_sentence(obj, fmt=fmt)}
    % if obj.alt_translation1:
        <div class="alt_translation">
            <span class="alt-translation alt-translation1 translation">${obj.alt_translation1}</span>
            <span class="alt-translation alt-translation1">[${obj.alt_translation_language1}]</span>
        </div>
    % endif
    % if obj.alt_translation2:
        <div class="alt_translation">
            <span class="alt-translation alt-translation2 translation">${obj.alt_translation2}</span>
            <span class="alt-translation alt-translation2">[${obj.alt_translation_language2}]</span>
        </div>
    % endif
    % if obj.audio:
        <div>
            ${u.cdstar.audio(obj.audio)}
        </div>
    % endif
    % if (obj.references or obj.source) and fmt == 'long':
        Source: ${h.linked_references(request, obj)|n} <span class="muted">${obj.source}</span>
    % endif
    <dl>
        % if obj.comment:
            <dt>Comment:</dt>
            <dd>
                ${u.add_unit_links(req, obj.dictionary, obj.comment)|n}
            </dd>
        % endif
        % if obj.type:
            <dt>${_('Type')}:</dt>
            <dd>${obj.type}</dd>
        % endif
        % for k, v in obj.datadict().items():
            <dt>${k}</dt>
            <dd>${v}</dd>
        % endfor
    </dl>
</%def>

<%def name="sentences(obj=None, fmt='long')">
    <% obj = obj or ctx %>
    <ul id="sentences-${obj.pk}" class="unstyled">
        % for a in obj.sentence_assocs:
            <li>
                <blockquote style="margin-top: 5px;">
                    ${h.link(request, a.sentence, label='%s %s:' % (_('Sentence'), a.sentence.number))}<br>
                    % if a.description and fmt == 'long':
                        <p>${a.description}</p>
                    % endif
                    ${sentence(a.sentence, fmt=fmt)}
                </blockquote>
            </li>
        % endfor
    </ul>
</%def>

<%def name="word_details()">
    <table class="table table-condensed table-nonfluid borderless">
        % if ctx.pos:
            <tr>
                <td><small>Part of Speech</small></td>
                <td>
                    <span class="vocabulary">${ctx.pos}</span>
                    % if links and 'pos' in links:
                        <small>${links['pos']|n}</small>
                    % endif
                </td>
            </tr>
        % endif
        % for value in ctx.unitvalues:
            <tr>
                <td>${h.link(request, value.unitparameter)}</td>
                <td>
                    <small>
                        ${value}
                        % if value.name:
                            (${value.name})
                        % endif
                    </small>
                </td>
            </tr>
        % endfor
        ${data_tr(ctx, links=links)}
    </table>

    ${'<ul class="unstyled">' if len(ctx.meanings) <= 1 else '<ol>'|n}
        % if links and 'de' in links:
            <li>
                <small>${links['de']|n}</small>
            </li>
        % endif
    % for m in ctx.meanings:
        <li>
            <ul class="unstyled">
                <li>
                    <strong>${u.add_unit_links(req, ctx.dictionary, m.name)|n}</strong>
                    % if 'Description' in m.sourcedict and m.sourcedict['Description']:
                        [${'; '.join(h.link(req, src) for src in m.sourcedict['Description']) | n}]
                    % endif
                    ##% if m.gloss and m.name != m.gloss:
                    ##    [${m.gloss}]
                    ##% endif
                </li>
                % if m.alt_translation1:
                    <li>
                        <span class="alt-translation alt-translation1">${u.add_unit_links(req, ctx.dictionary, m.alt_translation1)|n} [${m.alt_translation_language1}]</span>
                    </li>
                % endif
                % if m.alt_translation2:
                    <li>
                        <span class="alt-translation alt-translation2">${u.add_unit_links(req, ctx.dictionary, m.alt_translation2)|n} [${m.alt_translation_language2}]</span>
                    </li>
                % endif
                % if m.semantic_domain_list:
                    <li>
                        <ul class="inline semantic_domains_inline">
                            % for sd in m.semantic_domain_list:
                                <li><span class="vocabulary">${sd}</span></li>
                            % endfor
                        </ul>
                    </li>
                % endif
                <table class="table table-condensed table-nonfluid borderless">
                    ${data_tr(m)}
                    % for label, entries in m.related:
                        <tr>
                            <td><small>${label}</small></td>
                            <td>
                                <ul class="inline">
                                % for entry in entries:
                                    <li>${h.link(req, entry)}</li>
                                % endfor
                                </ul>
                            </td>
                        </tr>
                    % endfor
                </table>
                % if m.sentence_assocs:
                    <li>${sentences(m)}</li>
                % endif
            </ul>
        </li>
    % endfor
    ${'</ul>' if len(ctx.meanings) <= 1 else '</ol>'|n}

    <% rels = list(chain(ctx.links_to)) or list(chain(ctx.linked_from)) %>
    % if rels:
        <h4>Related entries</h4>
        <ul>
            % for desc, words in rels:
                <li>
                    % if desc:
                        <span>${desc}:</span>
                    % endif
                    <ul class="unstyled">
                        % for w in words:
                            <li>
                                <span style="margin-right: 10px">${h.link(request, w, title=w.name, label=w.label)|n}</span>
                                <strong>${u.add_unit_links(req, ctx.dictionary, '; '.join(w.description_list))|n}</strong>
                            </li>
                        % endfor
                    </ul>
                </li>
            % endfor
        </ul>
    % endif
</%def>
