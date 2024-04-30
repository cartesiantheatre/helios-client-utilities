#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# Define XML for menubar...
menu_xml = """
<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <menu id="ApplicationMenu">
    <submenu>
      <attribute name='label'>_File</attribute>
      <section>
        <item>
          <attribute name="label" translatable="yes">_End Session</attribute>
          <attribute name="action">win.end_session</attribute>
          <attribute name="icon">document-send</attribute>
        </item>
      </section>
      <section>
        <item>
          <attribute name="label" translatable="yes">_Quit</attribute>
          <attribute name="action">app.quit</attribute>
          <attribute name="accel">&lt;Primary&gt;q</attribute>
          <attribute name="icon">gtk-close</attribute>
          <attribute name="tooltip" translatable="yes">Quit application</attribute>
        </item>
      </section>
    </submenu>
    <submenu>
      <attribute name='label'>_Edit</attribute>
        <item>
          <attribute name="label" translatable="yes">_Preferences</attribute>
          <attribute name="action">app.preferences</attribute>
          <attribute name="icon">preferences-system</attribute>
        </item>
        <item>
          <attribute name="label" translatable="yes">Manual _Search Key</attribute>
          <attribute name="action">win.manual_search_key</attribute>
          <attribute name="icon">system-search</attribute>
        </item>
    </submenu>
    <submenu>
      <attribute name='label'>_View</attribute>
      <item>
        <attribute name="label" translatable="yes">_Fullscreen</attribute>
        <attribute name="action">win.fullscreen</attribute>
        <attribute name="accel">F11</attribute>
        <attribute name="icon">zoom-fit-best</attribute>
      </item>
      <!--item>
        <attribute name="label" translatable="yes">_Dark Mode</attribute>
        <attribute name="action">app.dark_mode</attribute>
        <attribute name="icon">night-light</attribute>
      </item-->
    </submenu>
    <submenu>
      <attribute name='label'>_Help</attribute>
      <section>
        <item>
          <attribute name="label" translatable="yes">_Website</attribute>
          <attribute name="action">app.website</attribute>
          <attribute name="icon">go-home</attribute>
        </item>
        <item>
          <attribute name="label" translatable="yes">_Report Issue</attribute>
          <attribute name="action">app.report_issue</attribute>
          <attribute name="icon">go-home</attribute>
        </item>
      </section>
      <section>
        <item>
          <attribute name="label" translatable="yes">_About</attribute>
          <attribute name="action">app.about</attribute>
          <attribute name="icon">dialog-warning</attribute>
        </item>
      </section>
    </submenu>
  </menu>
</interface>
"""

