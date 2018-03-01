<%inherit file="dictionaria.mako"/>
<%namespace name="util" file="util.mako"/>
<%! active_menu_item = "help" %>

<h2 id="Using the Dictionaria search fields">Using the Dictionaria search fields</h2>

<h3 id="Single column searches">Single column searches</h3>

<p>In the search fields above the different columns of the “Words (extra)” tab you can search for any sequence of characters. A character is a letter, digit, symbol, or a single blank space. Here are some examples of the different kinds of search strategies that can be employed:</p>

<br>
<table class="table table-bordered">
<thead>
	<tr>
	<td colspan="3">If you type into the search field:</td>
	<td>you can find, for example, the words or descriptions of this kind:</td>
	<td>The characters typed into the search field will match:</td>
	</tr>
</thead>
<tbody>
	<tr>
	<td colspan="3"><b>eat</b></td>
	<td><em>b<b>eat</b>; br<b>eat</b>h; <b>eat</b>; w<b>eat</b>her; …</em></td>
	<td>all entries with words containing  the character sequence <em>eat</em></td>
	</tr>
	<tr>
	<td colspan="3"><b>^eat<b></td>
	<td><em><b>eat</b>; <b>eat</b>er; <b>eat</b>ing; <b>Eat</b>on; …</em></td>
	<td>all entries with the character sequence <em>eat</em> at the <b>beginning</b> of the field</td>
	</tr>
	<tr>
	<td colspan="2"><b>^eat</b></td>
	<td>SPACE</td>
	<td><em><b>eat</b> an apple; <b>eat</b> meat; …</em></td>
	<td>all entries with the word <em>eat</em> at the beginning of the field followed by a space and more material</td>
	</tr>
	<tr>
	<td>SPACE</td>
	<td><b>eat</b></td>
	<td>SPACE</td>
	<td><em>dog <b>eat</b> dog; all plants which <b>eat</b> insects; …</em></td>
	<td>all entries with the word <em>eat</em> within the entry field</td>
	</tr>
	<tr>
	<td colspan="3"><b>ea$</b></td>
	<td><em>heartb<b>eat</b>; <b>eat</b>; m<b>eat</b>; tr<b>eat</b>; …</em></td>
	<td>all entries with the character sequence <em>eat</em> at the end of the field</td>
	</tr>
	<tr>
	<td colspan="2">SPACE</td>
	<td><b>eat$</b></td>
	<td><em>a bite to <b>eat</b>; fit to <b>eat</b>; …</em></td>
	<td>all entries with the word <em>eat</em> at the end of the field</td>
	</tr>
	<tr>
	<td colspan="3"><b>^eat$</b></td>
	<td><em>eat</em></td>
	<td>all entries containing exactly the character sequence <em>eat</em> in the entry field and nothing else</td>
	</tr>
</tbody>
</table>

<p>For searching the fields 'Part of speech' and 'Semantic domain' you can choose categories from the drop-down lists:</p>

<br>
<table class="table table-bordered">
<tr>
<td>Part of speech</td>
<td>The drop-down list shows all word classes and in some dictionaries classes of affixes and types of multi-word constructions. The abbreviations are listed in the respective introduction of the dictionary.</p>
</tr>
<tr>
<td>Semantic domain</td>
<td>The drop-down list shows a selection of semantic domains covered by the dictionary, for example 'plants' in the Daakaka and the Teop dictionary or 'botanical' in the Hdi dictionary.</td>
</tr>
</table>

<h3 id="Search across columns">Search across columns</h3>

<ol>
<li>Part of speech & meaning description
<br>
<p>For example, if you select 'v.tr' in 'part of speech' and enter 'hand' in 'meaning description' in the Teop dictionary, you find:</p>
<br>
<p><em>atoato</em>		'catch something with one's <strong>hand</strong>s'</p>
<p><em>kae</em>			'hold something in one <strong>hand</strong>'</p>
<p><em>poto</em>		'grab something or catch something with one's <strong>hand</strong>s'</p>
<br>
<p>In the Daakaka dictionary the search for 'v.tr' and 'hand' finds:</p>
<br>
<p><em>bwiti</em>		'break an elongated object in two with both <strong>hand</strong>s'</p>
<p><em>kinkate</em>		'hold something in one <strong>hand</strong>'</p>
<p><em>sedisi</em>		'raise a weapon (in one <strong>hand</strong>) to hit someone</p>
<p><em>tiwiye</em>		'break (something which can be broken easily with two <strong>hand</strong>s)</p>
</li>

<li>Part of speech and semantic domain
<br>
<p>For example, if you select 'v.itr' and 'body' you find 7 entries in the Daakaka dictionary, e.g.</p>
<br>
<p><em>banga</em>		'open one's mouth'</p>
<p><em>kyep</em>		'shit'</p>
<br>
<p>In the Teop dictionary the selection of 'v.intr' and 'body' finds 8 entried, e.g.</p>
<br>
<p><em>goroho</em>		'sleep'</p>
<p><em>kayuhu</em>		'spit'</p>

</li>
</ol>
