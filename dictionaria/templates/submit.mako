<%inherit file="home_comp.mako"/>
<%namespace name="util" file="util.mako"/>


<%def name="badge(style, icon)">
    <span class="badge badge-${style}"><i
            class="icon-${icon} icon-white">&nbsp;</i></span>
</%def>

<%def name="sidebar()">
    <div class="well toc">
        <h3>Contents</h3>
        <ol class="nested">
            <li>
                <a href="#overview">Overview: The five parts of the content structure</a>
                [<a href="#toolbox1">Toolbox help</a>]
            </li>
            <li>
                <a href="#introductory"><strong>The introductory text</strong></a>
                <ol class="nested">
                    <li><a href="#language">The language and its speakers</a></li>
                    <li><a href="#source">Source of the data </a></li>
                    <li><a href="#orthography">The orthography used in the dictionary </a>
                    </li>
                    <li><a href="#types">Types of special information </a></li>
                    <li><a href="#additional">Additional sections</a></li>
                </ol>
            </li>
            <li>
                <a href="#entry">The entry table</a>
                [<a href="#toolbox3">Toolbox help</a>]
            </li>
            <li>
                <a href="#sense">The sense table</a>
                [<a href="#toolbox4">Toolbox help</a>]
            </li>
            <li>
                <a href="#example">The example table</a>
                [<a href="#toolbox5">Toolbox help</a>]
            </li>
            <li>
                <a href="#references">The references table</a>
                [<a href="#toolbox6">Toolbox help</a>]
            </li>
        </ol>
    </div>
</%def>


<h2>General <em>Dictionaria</em> Submission Guidelines</h2>

<p><b>version of 9-1-2016</b></p>

<p>
    While the format of all <i>Dictionaria</i> dictionary publications will be a
    relational
    database, authors may also submit other (quasi-)database formats. We currently accept
    submissions in the following formats: .sfm, .db, .txt (e.g. from Toolbox, LexiquePro
    or FLEx), and .csv (e.g. exported from Excel or FileMaker). If you use a different
    format please contact us, so that we can see what we can do for you.
</p>
<p>
    A <i>Dictionaria</i> submission must consist of an <b>introductory text</b> and two to
    four files containing the following datasets: <b>entries</b>, <b>senses</b>, <b>examples</b>,
    and <b>references</b>. These datasets can be represented in tabular form and will
    function as our database tables; therefore, the files must be related via IDs as
    described in the sections below. The dictionary submission may also contain sound
    files, video files and image files.
</p>
<p>
    These Guidelines first describe the <b>content structure</b> of a submission, and then
    describe the <b>quality standards</b>. For some sections there will be some extra
    instructions for Toolbox/FLEx users, as we expect most contributions to reach us in
    that format, at least until new tools are established.
</p>
<p>
    Even though most <i>Dictionaria</i> submitters will submit their data in a well-known
    technical format, these Guidelines here describe the content structure without regard
    to a format, because the eventual publication is independent of any software
    environment. <i>Dictionaria</i> provides a web application for viewing and searching,
    but each dictionary should be thought of as a structured relational database that
    consists of (up to) four data tables plus (optionally) multimedia content.
</p>

<%util:section title="Overview: The five parts of the content structure" id="overview">
    <p>
        The most important principles of <i>Dictionaria</i> contributions, which
        distinguish them from many existing dictionaries, are:
    </p>
    <ul>
        <li>entries must not have subentries</li>
        <li>
            examples are optionally glossed as well as obligatorily translated, and are
            associated with senses, not entries as a whole
        </li>
        <li>
            multiple examples may be associated with one sense, and multiple senses with
            one (and the same) example (many-to-many relationship);
            <strong>one and the same example may illustrate the senses of different
                words</strong>
        </li>
    </ul>

    <dl>
        <dt>Part 1: The introductory prose text (<a href="#introductory">details in §2</a>)
        </dt>
        <dd>
            <p>This text must consist of at least of the following sections:</p>
            <ul>
                <li><b>the language and its speakers</b> (basic genealogical
                    sociolinguistic and geographical information)
                </li>
                <li><b>the source of the data</b> (information about texts and speakers
                    and how the author had access to them)
                </li>
                <li><b>the orthography</b> used in the dictionary (including a table
                    mapping special orthographic symbols to IPA symbols)
                </li>
                <li>the kinds of <b>special information</b> contained in the dictionary,
                    i.e. fields other than the obligatory fields and the other standard
                    fields
                </li>
            </ul>
        </dd>
        <dt>Part 2: The entry table (<a href="#entry">details in §3</a>)</dt>
        <dd>
            <figure class="well well-small">
                <a href="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot2.png">
                    <img class="size-medium wp-image-475 alignnone"
                         src="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot2-272x300.png"
                         alt="" width="272" height="300"
                         srcset="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot2-272x300.png 272w, http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot2.png 306w"
                         sizes="(max-width: 272px) 100vw, 272px"/>
                </a>
                <figcaption>Screenshot 1. The entry table</figcaption>
            </figure>
            <p>Each entry must contain information in the following three fields:</p>
            <ul>
                <li>(<b>entry) ID</b> (a unique alphanumeric code, chosen arbitrarily)
                </li>
                <li><b>headword</b> (= lemma, or citation form)</li>
                <li><b>part-of-speech</b></li>
            </ul>
            <p>In a simple wordlist, the entry table would also contain a field “sense”,
                but in more
                sophisticated dictionaries, an entry may have multiple senses. Thus, in
                <i>Dictionaria</i> there is a separate table containing the senses (Part 3
                below).
                Authors must make sure that each entry has at least one sense linked to
                it.
            </p>
            <p>In addition, an entry may have all kinds of further fields (see §3
                below).</p>
        </dd>
        <dt style="clear: right">Part 3: The sense table (<a href="#sense">details in
            §4</a>)
        </dt>
        <dd>
            <figure class="well well-small">
                <a href="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot22.png"><img
                        class="alignnone size-medium wp-image-478"
                        src="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot22-300x151.png"
                        alt="" width="300" height="151"
                        srcset="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot22-300x151.png 300w, http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot22.png 663w"
                        sizes="(max-width: 300px) 100vw, 300px"/></a>
                <figcaption>Screenshot 2. The sense table</figcaption>
            </figure>
            <p>The sense table contains all the senses, which are represented in the
                dictionary. Each
                sense is linked to exactly one entry, but entries may have multiple senses
                linked to
                them (e.g. German <i>spinnen</i> 1. ‘spin’ 2. ‘be crazy’). There is thus a
                many-to-one
                relationship between senses and entries.</p>
            <p>Each sense must minimally contain information in the following three fields
                (again, the
                ID is a code that can be chosen arbitrarily):</p>
            <ul>
                <li><b>(sense) ID</b></li>
                <li><b>sense description (= list of semicolon-delimited sense
                    descriptors)</b></li>
                <li><b>ID of related entry</b></li>
            </ul>
            <p>Since a sense may be illustrated by multiple examples, there is a separate
                table
                containing the examples (Part 4 below).</p>
            <p>In addition, a sense may contain multimedia content, the field “semantic
                domain” and
                association fields relating to meaning (see §4 below), as well as comments
                and
                references fields.</p>
        </dd>
        <dt style="clear: right">Part 4: The example table (<a href="#example">details in
            §5</a>)
        </dt>
        <dd>
            <figure class="well well-small">
                <a href="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot3.png"><img
                        class="alignnone size-medium wp-image-481"
                        src="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot3-300x73.png"
                        alt="" width="300" height="73"
                        srcset="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot3-300x73.png 300w, http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot3-768x188.png 768w, http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot3.png 859w"
                        sizes="(max-width: 300px) 100vw, 300px"/></a>
                <figcaption>Screenshot 3. The example table</figcaption>
            </figure>
            <p>
                The example table contains all the examples which are represented in the
                dictionary.
                Each example is linked to one or more senses, and senses may have multiple
                examples
                linked to them. There is thus a many-to-many relationship between examples
                and
                senses.
            </p>
            <p>Each example must minimally contain information in the following four
                fields:
            </p>
            <ul>
                <li><b>(example) ID</b></li>
                <li><b>primary text</b></li>
                <li><b>translation</b></li>
                <li><b>list of IDs of related senses </b>(this is a list, not a single ID,
                    because an example may illustrate several senses)
                </li>
            </ul>
            <p>In addition, there should be a field “interlinear gloss”, a field “example
                source”, and
                optionally also “analyzed text” (with morpheme-by-morpheme segmentations).
                There may
                also be other fields (see §5 below).</p>
        </dd>
        <dt style="clear: right">Part 5: The references table (<a href="#references">details
            in §6</a>)
        </dt>
        <dd>
            <figure class="well well-small">
                <a href="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot4.png"><img
                        class="alignnone size-medium wp-image-482"
                        src="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot4-300x103.png"
                        alt="" width="300" height="103"
                        srcset="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot4-300x103.png 300w, http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot4.png 547w"
                        sizes="(max-width: 300px) 100vw, 300px"/></a>
                <figcaption>Screenshot 4. The references table</figcaption>
            </figure>
            <p>A bibliographical reference must contain information on the standard bib
                fields:</p>
            <ul>
                <li><b>(reference) ID</b></li>
                <li><b>author</b></li>
                <li><b>year</b></li>
                <li><b>title of paper</b></li>
                <li>(and so on)</li>
            </ul>
        </dd>
    </dl>
</%util:section>

<%util:section title="The introductory text" id="introductory">
    <p>
        As noted in §1, the introductory text, giving background information on the
        language and the dictionary, must consist of at least four standard sections,
        discussed
        further in §2.1-4 below. Further sections may be added (see §2.5).
    </p>

    <h4><a name="language"></a>The language and its speakers</h4>
    <p>
        This section contains basic sociohistorical and geographical information on the
        language, including
    </p>
    <ul>
        <li>
            name of the language (possibly with discussion of other names that have been
            used elsewhere)
        </li>
        <li>ISO und Glottolog code</li>
        <li>names and codes of languages other than English that are used for sense
            descriptions and example translations
        </li>
        <li>genealogical affiliation</li>
        <li>approximate number of speakers, location of speakers</li>
        <li>social role of the language, multilingualism, literacy</li>
        <li>the most important earlier work by linguists and anthropologists on the
            language
        </li>
    </ul>

    <h4><a name="source"></a>Source of the data</h4>
    <p>
        It is very important for dictionaries of under-researched languages to give
        detailed
        information on the source of the data, so that the reliability of the data can be
        assessed and the input of speakers and assistants is acknowledged. In addition to
        giving the names of the people involved and their role, this section should also
        specify the times and places where the data were gathered, should give background
        information on the corpora that were the basis for the word collections, should
        list
        earlier or related dictionaries that may have been used, and possibly describe
        elicitation methods.
    </p>

    <h4><a name="orthography"></a>The orthography used in the dictionary</h4>
    <p>
        A dictionary should use a consistent orthography, especially for the headwords,
        regardless of whether the speakers use the language for writing or not. If the
        orthography uses non-IPA symbols (as will generally be the case), this section
        should
        contain a table mapping all orthographic symbols to IPA symbols.
    </p>
    <p>
        If the language is normally written in a non-Latin script, this should also be
        given
        for each entry (and each form), but the headwords given in Latin script will be
        regarded as the primary representation.
    </p>
    <p>
        This section may contain the alphabet (i.e. the ordered list of graphemes) used by
        the
        language, but it should be noted that any special sorting conventions will not be
        used
        in <i>Dictionaria</i>. (The sorting algorithm that is used is called DUCET, which
        is
        the default for Unicode characters.)
    </p>
    <p>
        The section may also contain further discussion of the orthography, e.g.
        concerning its
        history, its specific properties, principles for word division, treatment of
        spelling
        variants, and so on.
    </p>

    <h4><a name="types"></a>Types of special information</h4>
    <p>
        This section lists the special fields contained in the dictionary, i.e. fields
        other
        than the obligatory fields and the other standard fields. For example, for some
        languages a dictionary might provide specific grammatical information (on
        inflection
        class, gender, classifier usage, etc.), other dictionaries might provide extensive
        information on spelling variants, dialectal variants or loanword provenance.
    </p>
    <p>
        For each field with a restricted number of values, all values must be listed and
        described here (e.g. parts-of-speech, or semantic domains).
    </p>
    <p>
        If any abbreviations are used, they also need to be explained here. However, in
        general
        the use of abbreviations is strongly discouraged, as abbreviations are far less
        necessary in electronic publication than in paper-based publication, as there are
        (almost) no space limitations
    </p>

    <h4><a name="additional"></a>Additional sections</h4>
    <p>The introductory text may contain additional sections, e.g.</p>
    <ul>
        <li>further grammatical notes</li>
        <li>cultural notes</li>
        <li>explaining in more detail the expected use of the dictionary</li>
        <li>discussion of the size of the dictionary (number of entries, number of
            multimedia files, etc.)
        </li>
        <li>an acknowledgement section (e.g. listing native speaker assistants) at the end
            of the introductory text
        </li>
    </ul>
</%util:section>

<%util:section title="The entry table" id="entry">
    <p>
        As noted in §1, each entry in the entry table must contain information in the
        following three fields:
    </p>
    <ul>
        <li>(<b>entry) ID</b> (a unique alphanumeric code)</li>
        <li><b>headword</b></li>
        <li><b>part-of-speech</b></li>
    </ul>
    <p>
        The ID can be chosen arbitrarily, and in principle, it would be possible to use
        the
        headword as ID, with a distinguishing number when there are homonyms. For the
        purposes
        of the database, we need to keep the ID and the headword separate, so it is
        recommended to choose an arbitrary code (e.g. a number) as the ID.
    </p>
    <p>
        The headword (or lemma) is the name of the entry. It is most often the citation
        form of
        a lexeme, but it may also be any inflected form such as <i>went </i>in English
        dictionaries, a root, an affix, or a multi-word expression (such as phrasal verbs,
        frequent or lexicalised collocations and idiomatic phrases).
    </p>
    <p>
        The part-of-speech field contains information such as “verb”, “noun”, and for
        multi-word lemmas either simply &#8222;phrase&#8220; or a language specific term
        such
        as &#8222;phrasal verb&#8220; or &#8222;serial verb&#8220; can be used. Language
        specific terms must be definted in the introduction..
    </p>
    <p>
        Since an entry can have multiple senses, the entry table does not contain sense
        information, and there is a separate table containing the senses. For each entry,
        there must be at least one sense.
    </p>
    <p>
        In addition, an entry may have all kinds of further fields, whether <b>standard
        fields</b> (which have the same meaning across languages) or <b>language-specific
        fields</b> (which are defined depending on the language’s system, or peculiarities
        of
        the culture).
    </p>
    <figure class="well well-small">
        <a href="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot5.png">
            <img class="alignnone size-medium wp-image-489"
                 src="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot5-300x136.png"
                 alt="" width="300" height="136"
                 srcset="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot5-300x136.png 300w, http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot5.png 544w"
                 sizes="(max-width: 300px) 100vw, 300px"/>
        </a>
        <figcaption>Screenshot 5. The entry table with fields for original script and
            sound
            files
        </figcaption>
    </figure>
    <p>Examples of <b>standard fields</b> are:</p>
    <ul>
        <li><b>lemma in original script</b></li>
        <li><b>pronunciation of lemma</b></li>
        <li><b>variant form</b></li>
        <li><b>general comments</b></li>
        <li><b>bibliographical references </b>(list of bibref IDs)</li>
        <li><b>etymological origin</b></li>
        <li><b>source language (for loanwords) </b></li>
        <li><b>source word (for loanwords)</b></li>
    </ul>
    <p>For sound files, images, and video clips there are separate fields</p>
    <ul>
        <li><b>sound file ID</b></li>
    </ul>
    <p>Examples of <b>language-specific fields</b> are:</p>
    <ul>
        <li>gender</li>
        <li>inflectional class</li>
        <li>form in divergent dialect X</li>
        <li>sociolinguistic information such as literary vs. colloquial, obsolete, taboo,
            etc.
        </li>
    </ul>
    <figure class="well well-small" style="clear: right">
        <a href="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot6.png">
            <img
                    class="alignnone size-medium wp-image-491"
                    src="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot6-300x152.png"
                    alt="" width="300" height="152"
                    srcset="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot6-300x152.png 300w, http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot6.png 631w"
                    sizes="(max-width: 300px) 100vw, 300px"/>
        </a><br/>
        <figcaption>Screenshot 6. The entries table with an association field (it
            contains)
        </figcaption>
    </figure>
    <p>
        Finally, an entry can contain (standard or language-specific) <b>association
        fields</b>,
        i.e. fields that establish a relationship between the entry and some other entry.
        The content of an association field is a list of entry IDs. The name of an
        association
        field is relational, i.e. it is a transitive or copula verb or ends in a
        preposition, e.g.
    </p>
    <ul>
        <li><b>it contains</b> (list of entry IDs)</li>
        <li><b>its causative is</b> (list of entry IDs)</li>
        <li><b>its numeral classifier is</b> (list of entry IDs)</li>
        <li><b>see also</b> (for generally related entries)</li>
    </ul>
    <p>
        Association fields are optional, but if a <i>Dicitonaria</i> contribution makes
        use of
        one or more of them, then we encourage the authors to do so in a consistent and
        comprehensive way.
    </p>
    <p>
        Note that <i>Dictionaria</i> contributions must not have subentries; what would be
        treated as a subentry in a linear dictionary is treated as a separate (but
        associated) entry in <i>Dictionaria</i>.
    </p>
    <p>
        Entries with multi-word lemmas such as <i>take part </i>would be associated with
        <i>take</i> and <i>part</i> via association fields (it contains (list of IDs)).
    </p>
</%util:section>

<%util:section title="The sense table" id="sense">
    <p>
        As noted in §1, each sense must minimally contain information in the following
        three fields:
    </p>
    <ul>
        <li><b>(sense) ID</b></li>
        <li><b>sense description (in English)</b></li>
        <li><b>ID of related entry</b></li>
    </ul>
    <p>
        Since a sense may be illustrated by multiple examples and the words in one example
        may
        illustrate senses of different entries there is a separate table containing the
        examples.
    </p>
    <p>
        The sense description (= definition) is a list of semicolon-delimited <b>sense
        descriptors</b>.which may be translation equivalents or explanations. They are
        semicolon-delimited because a sense descriptor itself could contain a comma (e.g.
        “big, expensive boat”).
    </p>
    <figure class="well well-small">
        <a href="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot7-1.png"><img
                class="alignnone size-medium wp-image-496"
                src="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot7-1-300x91.png"
                alt="" width="300" height="91"
                srcset="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot7-1-300x91.png 300w, http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot7-1-768x232.png 768w, http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot7-1.png 1005w"
                sizes="(max-width: 300px) 100vw, 300px"/></a>
        <figcaption>Screenshot 7. The sense table with fields for scientific name,
            semantic domain
            and an association field (is synonymous with)
        </figcaption>
    </figure>
    <p>In addition, a sense may contain the following standard fields:</p>
    <ul>
        <li><b>list of semicolon -delimited semantic domains</b></li>
        <li><b>scientific name (for plant and animal species)</b></li>
        <li><b>comments on sense</b><br/></li>
        <li><b>bibliographical references </b>(list of bibref IDs)</li>
        <li><b>sense description in the source language with a translation into the target
            language</b></li>
    </ul>
    <p>
        Note that a “gloss” field, as used in Toolbox for glossing purposes, is not
        relevant for <i>Dictionaria</i> contributions.
    </p>
    <p>
        Senses may also contain language-specific sense descriptions, especially
        descriptions
        in a major additional language spoken by many speakers (e.g. Spanish for
        indigenous
        languages of Mexico, Indonesian for languages of Indonesia, etc.):
    </p>
    <ul>
        <li><b>sense description in language X</b></li>
    </ul>
    <p>Like entries, senses can contain fields for associated senses, e.g.</p>
    <ul>
        <li><b>is synonymous with </b>(list of sense IDs)</li>
        <li><b>is antonymous with </b>(list of sense IDs)</li>
    </ul>
</%util:section>

<%util:section title="The example table" id="example">
    <figure class="well well-small">
        <a href="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot8.png"><img
                class="alignnone size-medium wp-image-499"
                src="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot8-300x40.png"
                alt="" width="300" height="40"
                srcset="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot8-300x40.png 300w, http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot8-768x101.png 768w, http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot8-1024x135.png 1024w, http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/screenshot8.png 1344w"
                sizes="(max-width: 300px) 100vw, 300px"/></a>
        <figcaption>Screenshot 8. The example table with fields for interlinear gloss and
            source
        </figcaption>
    </figure>
    <p>
        As noted earlier, each example must minimally contain information in the following
        four fields:
    </p>
    <ul>
        <li><b>(example) ID</b></li>
        <li><b>primary text</b></li>
        <li><b>interlinear gloss </b>(not obligatory</li>
        <li><b>translation </b>(into English)</li>
        <li><b>list of IDs of related senses </b>(this is a list, not a single ID, because
            an example may illustrate several senses)
        </li>
        <li><b>source of example </b>(initially not obligatory; bibliographical or corpus
            reference; <b>name of speaker </b>who provided the example)
        </li>
    </ul>
    <p>
        In addition, there may be further standard fields (and perhaps also
        language-specific fields):
    </p>
    <ul>
        <li><b>analyzed text</b> (e.g. morphemes, or more abstract morphophonological
            representation)
        </li>
        <li><b>literal translation</b></li>
        <li><b>date </b>(of data collection)</li>
    </ul>
</%util:section>

<%util:section title="The references table" id="references">
    <p>A bibliographical reference must contain information on the standard bib fields
        (cf. the Generic Style Rules for Linguistics):
    </p>
    <ul>
        <li><b>(bibref) ID</b></li>
        <li><b>publication type </b>(journal article, book, book part, thesis, misc)</li>
        <li><b>author list</b></li>
        <li><b>year</b></li>
        <li><b>article title</b></li>
        <li><b>editor list</b></li>
        <li><b>publication title</b></li>
        <li><b>volume number</b></li>
        <li><b>page numbers</b></li>
        <li><b>city</b></li>
        <li><b>publisher</b></li>
    </ul>
    <p>Of course, different publication types use different subsets of these fields.</p>
</%util:section>

<h3><i>Dictionaria </i> Submission Guidelines Commentary for Toolbox Users</h3>
<p><i>version of 10/23/2016</i></p>
<p>
    If you are planning to submit a Toolbox database to <i>Dictionaria</i>, you will find
    these hints helpful. We strongly encourage you to first read our general submission
    guidelines thoroughly and then use these extra guidelines as a commentary. The Toolbox
    tips follow the outline of the general guidelines. For each section, that may be
    confusing to Toolbox users we will explain here what this means and entails for you.
</p>
<p>
    All Toolbox submissions to <i>Dictionaria</i> should generally consist of a Dictionary
    text file (.txt, .db), an examples text file (.txt, .db) and their corresponding .typ
    files. If you are using the MDF 4.0 templates without any modifications or extra
    fields then you do not need to send in the .typ files. If you are using an orthography
    in one of your dictionary fields, which is not Latin based, and/or has special
    characters, then you need to also send us the associated .lng (Language encoding)
    file.
</p>
<p>
    In addition to your Toolbox files, we ask you to also send us a prose description as
    described in §2 in the general guidelines.
</p>

<%util:section title="Re: Overview: The five parts of the content structure" id="toolbox1" level="4">
    <p>
        ${badge('important', 'exclamation-sign')} no subentries
    </p>
    <p>
        We cannot accept submissions with subentries, as they do not fit into our general
        data
        model. If you have made use of the <span class="label">\se</span> field in
        Toolbox, you need to go through each
        and every one of them and turn them into new entries. You may then use a reference
        field, such as <span class="label">\cf</span> to link them to the original entry
        (see also “association fields”
        below). If you have made use of the <span class="label">\se</span> field in a
        completely consistent way, you may
        contact us, as we may be able to help you in turning these subentries into new
        entries
        (semi-)automatically. This is only possible if your field structure is fully
        consistent and transparent.
    </p>
    <p>
        ${badge('info', 'question-sign')} What does this mean?
    </p>
    <p>An entry like this:</p>
    <p class="well well-small">
        <a href="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox1.png"><img
                class="alignnone size-full wp-image-501"
                src="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox1.png"
                alt="" width="290" height="170"/></a></p>
    <p>Will need to become two entries like so:</p>
    <p class="well well-small">
        <a href="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox2.png"><img
                class="alignnone size-medium wp-image-502"
                src="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox2-300x98.png"
                alt="" width="300" height="98"
                srcset="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox2-300x98.png 300w, http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox2.png 580w"
                sizes="(max-width: 300px) 100vw, 300px"/></a></p>
    <p>${badge('important', 'exclamation-sign')} examples</p>
    <p>
        Toolbox is set up to have example sentences stored directly in each dictionary
        entry.
        However, we strongly advise you to store example sentences in a separate text file
        instead and to simply list their sentence IDs in the dictionary entry. An
        advantage of
        keeping example sentences in a separate text file is that you can link them to
        different entries rather than copying them into several entries and thus risking
        inconsistencies. You can simply use the <span class="label">\xref</span> field to
        refer to the corresponding <span class="label">\ref</span>
        field in your examples text file. Another advantage of keeping your examples in a
        separate text file is that you may use Toolbox to help you parse and gloss them.
    </p>
    <p>
        ${badge('info', 'question-sign')} What does this mean?
    </p>
    <p>Entries like the one here (using <span class="label">\xv</span> and <span
            class="label">\xe</span>):</p>
    <p class="well well-small">
        <a href="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox3.png"><img
                class="alignnone size-full wp-image-504"
                src="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox3.png"
                alt="" width="250" height="190"/></a></p>
    <p>
        should look like this instead, with the example being stored in a separate text
        file
        (glossing is optional):
    </p>
    <p class="well well-small">
        <a href="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox4.png"><img
                class="alignnone size-medium wp-image-505"
                src="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox4-300x91.png"
                alt="" width="300" height="91"
                srcset="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox4-300x91.png 300w, http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox4.png 560w"
                sizes="(max-width: 300px) 100vw, 300px"/></a></p>
    <p>
        This way you can link one example sentence to several entries without creating
        inconsistent copies of one and the same sentence, e.g. in the entry below the same
        example can be listed as in the one above:
    </p>
    <p class="well well-small">
        <a href="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox5.png"><img
                class="alignnone size-full wp-image-508"
                src="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox5.png"
                alt="" width="160" height="190"/></a></p>
    <p>
        If you already have a Toolbox dictionary with example sentence, then please
        contact us,
        so that we can assist you in extracting them and storing them in a new text file
        (see
        also “Re: 5. The examples table” below)
    </p>
    <p>
        (the rest of §1 does not need any further explanation here, as each topic is
        covered in
        a more detailed section later on the in the general guidelines)
    </p>
</%util:section>

<%util:section title="Re: Overview: The entry table" id="toolbox3" level="4">
    <p>
        This section describes what the entry table would look like in a relational
        database,
        as a Toolbox user you do not have a separate entry table, instead your dictionary
        file
        is a combination of the entry table and the sense table.
    </p>
    <p>${badge('important', 'exclamation-sign')} entry
        ID ${badge('info', 'question-sign')} What does this mean?</p>
    <p>
        The entry ID in Toolbox are the contents of the <span class="label">\lx</span>
        field (in combination with the <span class="label">\hm</span>
        field where necessary). You do not need to assign alphanumerical codes to your
        entries. In Toolbox your headword is the entry ID.
    </p>
    <p>${badge('important', 'exclamation-sign')} part-of-speech</p>
    <p>
        To ensure consistency we strongly encourage you to use a range set in Toolbox for
        the
        <span class="label">\ps</span> field. This will help you in avoiding typos or
        multiple abbreviations for one and
        the same thing. In fact, if possible do not use abbreviations at all. Do not use
        more
        than one <span class="label">\ps</span> field per entry. If you have headwords
        which belong to two different word
        categories, you should create two entries.
    </p>
    <p>${badge('important', 'exclamation-sign')} media files</p>
    <p>
        For media files (sound, images) simply use the Toolbox convention of listing the
        file
        name and its extension in the corresponding MDF field (<span
            class="label">\sf</span> [sound file illustrating
        the headword], <span class="label">\sfx</span> [soundfile of an example], <span
            class="label">\pc</span> [picture]). You can then send us
        your files and we can then display them in your <i>Dictionaria</i> entries. If you
        also have videos you want to include, please contact us, and we will try to find a
        way
        to accommodate them.
    </p>
    <p>${badge('important', 'exclamation-sign')} association
        fields ${badge('info', 'question-sign')} What does this mean?</p>
    <p>
        What is called an association field in the <i>Dictionaria</i> submission
        guidelines
        also exists in Toolbox. Fields such as <span class="label">\cf</span> or <span
            class="label">\syn</span> are examples of such fields. If you
        have made use of association fields in Toolbox, you simply need to tell us which
        ones
        you have used, and what kind of association relation they represent. In these
        association fields the headwords to which your entry is related should be listed.
        You
        can also come up with your own association fields if necessary and use them in
        Toolbox
        (e.g. if you want to link inchoatives to their causatives, introduce a field
        called
        <span class="label">\caus</span> and then list the related headword in it).
        Remember headwords are your entry
        IDs. If you have multiple entries to which an entry is related in one and the same
        way, you may list the associated entries in the same field separated by a
        semicolon.
        (E.g. if <span class="label">\lx</span> drowdaeh is associated to <span
            class="label">\lx</span> drow and <span class="label">\lx</span> daeh, you may
        have an field
        <span class="label">\cf</span> drow ; daeh)
    </p>
</%util:section>

<%util:section title="Re: Overview: The sense table" id="toolbox4" level="4">
    <p>
        As a Toolbox user you will not have a separate sense table. Your senses are part
        of
        your dictionary file. Sense descriptions should be given in the <span
            class="label">\de</span> field.</p>
    <p>${badge('important', 'exclamation-sign')} entry
        ID ${badge('info', 'question-sign')} What does this mean?
    </p>
    <p>
        The sense IDs in Toolbox are the contents of the <span class="label">\de</span>
        field. You do not need to assign
        alphanumerical codes to your entries.
    </p>
    <p>${badge('important', 'exclamation-sign')} multiple senses in an entry</p>
    <p>If an entry has multiple senses, we strongly recommend that you use the sense
        number
        field (<span class="label">\sn</span>) to indicate this. This will structure the
        entry much better than using two
        <span class="label">\de</span> fields in a random place your entry. the <span
                class="label">\sn</span> field should contain simply the
        number of the sense (1, 2, 3, etc.) and be followed by a de field. Look at the
        entry
        below, for a good illustration of sense numbering:</p>
    <p class="well well-small">
        <a href="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox6.png"><img
                class="alignnone size-medium wp-image-509"
                src="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox6-300x192.png"
                alt="" width="300" height="192"
                srcset="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox6-300x192.png 300w, http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox6.png 320w"
                sizes="(max-width: 300px) 100vw, 300px"/></a></p>
    <p>With the senses cleanly separated, you can also assign different semantic domains
        and
        different example sentences to each sense, as also illustrated in the
        screenshot.</p>
</%util:section>

<%util:section title="Re: Overview: The example table" id="toolbox5" level="4">
    <p>As already mentioned above, Toolbox is generally set up to list example sentences
        in
        the respective entries directly. This is where we at <i>Dictionaria </i>would like
        you
        not to follow the Toolbox conventions for the reasons stated above. If you have
        already created a database that includes example sentences then please get in
        touch
        with us so that we can help you in extracting them into a separate file while at
        the
        same time checking for inconsistences.</p>
    <p>For your example sentences you can simply use a regular Toolbox Text file, with the
        common fields <span class="label">\ref</span>, <span class="label">\tx</span> and
        <span class="label">\ft</span>. If you can also gloss your example sentences then
        use
        <span class="label">\mb</span> and <span class="label">\gl</span> as well.</p>
    <p>Here is an illustration of what such an example sentence text file could look
        like:</p>
    <p class="well well-small">
        <a href="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox7.png"><img
                class="alignnone size-medium wp-image-510"
                src="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox7-300x195.png"
                alt="" width="300" height="195"
                srcset="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox7-300x195.png 300w, http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox7.png 400w"
                sizes="(max-width: 300px) 100vw, 300px"/></a></p>
    <p>With your dictionary being a scientific publication we also expect you to list
        sources
        for where your example sentence came from, this can either be a bibliographical
        reference, a corpus reference or the name of (or code for) a(n anonymized) native
        speaker of the language. In the screenshot above the <span
                class="label">\so</span> (source) field has been used
        to store this information.</p>
</%util:section>

<%util:section title="Re: Overview: The references table" id="toolbox6" level="4">
    <p>We advise you to send us a list of references in a format that is not Toolbox. If
        you
        are already storing full bibliographical references in Toolbox then contact us and
        we
        will find a way to deal with it, but it is more advisable to send us a simple
        spreadsheet list of all full references and then to only list short versions or
        IDs to
        them of that in any Toolbox reference field.</p>
    <p>
        ${badge('info', 'question-sign')} What does this mean?
    </p>
    <p>In the screenshot below an example sentence is listed as having a source
        RE0001:</p>
    <p class="well well-small">
        <a href="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox8.png"><img
                class="alignnone size-medium wp-image-511"
                src="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox8-300x61.png"
                alt="" width="300" height="61"
                srcset="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox8-300x61.png 300w, http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox8.png 590w"
                sizes="(max-width: 300px) 100vw, 300px"/></a></p>
    <p>This reference can be retrieved from a spreadsheet which follows the general
        submission
        guidelines like so:</p>
    <p class="well well-small">
        <a href="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox9.png"><img
                class="alignnone size-medium wp-image-512"
                src="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox9-300x84.png"
                alt="" width="300" height="84"
                srcset="http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox9-300x84.png 300w, http://home.uni-leipzig.de/dictionaryjournal/wp-content/uploads/2016/12/toolbox9.png 450w"
                sizes="(max-width: 300px) 100vw, 300px"/></a></p>
</%util:section>


<div class="alert alert-info"><b>If you have any questions concerning your Toolbox
    database and the possibility to
    publish with </b><b><i>Dictionaria</i></b><b>, then please just get in touch with us,
    we will try to help you the best we can to fit it into our data model. Don’t let “tech
    talk” discourage you</b>
    <p><b><i>✉ dictionary.journal@uni-leipzig.de</i></b></p>
</div>
