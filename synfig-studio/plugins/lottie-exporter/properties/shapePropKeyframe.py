# pylint: disable=line-too-long
"""
Will store all the functions and modules for generation of shapPropKeyframe file
in Lottie format
"""

import sys
import ast
from lxml import etree
from misc import get_frame, Vector, is_animated, radial_to_tangent
from properties.multiDimensionalKeyframed import gen_properties_multi_dimensional_keyframed
from properties.valueKeyframed import gen_value_Keyframed
from synfig.animation import get_vector_at_frame, get_bool_at_frame, gen_dummy_waypoint
sys.path.append("../")


def animate_radial_composite(radial_composite, window):
    """
    Animates the radial composite and updates the window of frame if radial
    composite's parameters are already animated
    Also generate the Lottie path and stores in radial_composite

    Args:
        radial_composite (lxml.etree._Element) : Synfig format radial composite-> stores radius and angle
        window           (dict)                : max and min frame of overall animations stored in this

    Returns:
        (None)
    """
    for child in radial_composite:
        if child.tag == "radius":
            radius = child
        elif child.tag == "theta":
            theta = child
    update_frame_window(radius[0], window)
    update_frame_window(theta[0], window)

    radius = gen_dummy_waypoint(radius, "radius", "real")
    theta = gen_dummy_waypoint(theta, "theta", "region_angle")

    # Update the newly computed radius and theta
    update_child_at_parent(radial_composite, radius, "radius")
    update_child_at_parent(radial_composite, theta, "theta")

    # Generating the radial path and store in the lxml element
    radius_dict = {}
    gen_value_Keyframed(radius_dict, radius[0], 0)
    # Store in lxml element
    radius_lxml = etree.Element("radius_path")
    radius_lxml.text = str(radius_dict)
    radial_composite.append(radius_lxml)

    # Generating the theta path and store in the lxml element
    theta_dict = {}
    gen_value_Keyframed(theta_dict, theta[0], 0)
    # Store in lxml element
    theta_lxml = etree.Element("theta_path")
    theta_lxml.text = str(theta_dict)
    radial_composite.append(theta_lxml)


def update_frame_window(node, window):
    """
    Given an animation, finds the minimum and maximum frame at which the
    waypoints are located

    Args:
        node    (lxml.etree._Element) : Animation to be searched in
        window  (dict)                : max and min frame will be stored in this

    Returns:
        (None)
    """
    if is_animated(node) == 2:
        for waypoint in node:
            fr = get_frame(waypoint)
            if fr > window["last"]:
                window["last"] = fr
            if fr < window["first"]:
                window["first"] = fr


def update_child_at_parent(parent, new_child, tag):
    """
    Given a node, replaces the child with tag `tag` with new_child

    Args:
        parent    (lxml.etree._Element) : Node whose child needs to be replaced
        new_child (lxml.etree._Element) : Updated child of the parent
        tag       (str)                 : To identify the appropriate child

    Returns:
        (None)
    """
    for chld in parent:
        if chld.tag == tag:
            chld.getparent().remove(chld)
    parent.insert(0, new_child)


def get_tangent_at_frame(t1, t2, split_r, split_a, fr):
    """
    Given a frame, returns the in-tangent and out-tangent at a bline point
    depending on whether split_radius and split_angle is "true"/"false"

    Args:
        t1      (lxml.etree._Element) : Holds Tangent 1/In Tangent
        t2      (lxml.etree._Element) : Holds Tangent 2/Out Tangent
        split_r (lxml.etree._Element) : Holds animation of split radius parameter
        split_a (lxml.etree._Element) : Holds animation of split angle parameter
        fr      (int)                 : Holds the frame value

    Returns:
        (misc.Vector, misc.Vector) : In-tangent and out-tangent at the given frame
    """

    # Get value of split_radius and split_angle at frame
    sp_r = get_bool_at_frame(split_r[0], fr)
    sp_a = get_bool_at_frame(split_a[0], fr)

    # Setting tangent 1
    for chld in t1:
        if chld.tag == "radius_path":
            dictionary = ast.literal_eval(chld.text)
            r1 = get_vector_at_frame(dictionary, fr)
        elif chld.tag == "theta_path":
            dictionary = ast.literal_eval(chld.text)
            a1 = get_vector_at_frame(dictionary, fr)
    x, y = radial_to_tangent(r1, a1)
    tangent1 = Vector(x, y)

    # Setting tangent 2
    for chld in t2:
        if chld.tag == "radius_path":
            dictionary = ast.literal_eval(chld.text)
            r2 = get_vector_at_frame(dictionary, fr)
            if sp_r == "false":
                # Use t1's radius
                r2 = r1
        elif chld.tag == "theta_path":
            dictionary = ast.literal_eval(chld.text)
            a2 = get_vector_at_frame(dictionary, fr)
            if sp_a == "false":
                # Use t1's angle
                a2 = a1
    x, y = radial_to_tangent(r2, a2)
    tangent2 = Vector(x, y)
    return tangent1, tangent2


def gen_bline_shapePropKeyframe(lottie, bline_point):
    """
    Generates the dictionary corresponding to properties/shapePropKeyframe.json,
    given a bline/spline

    Args:
        lottie     (dict) : Lottie generated keyframes will be stored here for shape/path
        bline_path (lxml.etree._Element) : shape/path store in Synfig format

    Returns:
        (None)
    """
    ################### SECTION 2 #########################
    # Inserting waypoints if not animated and finding the first and last frame
    # AFter that, there path will be calculated in lottie format which can
    # latter be used in get_vector_at_frame() function
    window = {}
    window["first"] = sys.maxsize
    window["last"] = -1

    for entry in bline_point:
        composite = entry[0]
        for child in composite:
            if child.tag == "point":
                pos = child
            elif child.tag == "t1":
                t1 = child
            elif child.tag == "t2":
                t2 = child
            elif child.tag == "split_radius":
                split_r = child
            elif child.tag == "split_angle":
                split_a = child

        # Necassary to update this before inserting new waypoints, as new
        # waypoints might include there on time: 0 seconds
        update_frame_window(pos[0], window)

        # Empty the pos and fill in the new animated pos
        pos = gen_dummy_waypoint(pos, "point", "vector")
        update_child_at_parent(composite, pos, "point")

        split_r = gen_dummy_waypoint(split_r, "split_radius", "bool")
        update_child_at_parent(composite, split_r, "split_radius")

        split_a = gen_dummy_waypoint(split_a, "split_angle", "bool")
        update_child_at_parent(composite, split_r, "split_angle")

        # Generate path for Lottie format
        path_dict = {}
        gen_properties_multi_dimensional_keyframed(path_dict, pos[0], 0)
        # Store in lxml element
        path_lxml = etree.Element("point_path")
        path_lxml.text = str(path_dict)
        composite.append(path_lxml)

        animate_radial_composite(t1[0], window)
        animate_radial_composite(t2[0], window)

    # Minimizing the window size
    if window["first"] == sys.maxsize and window["last"] == -1:
        window["first"] = window["last"] = 0
    ################# END OF SECTION 1 ###################

    ################ SECTION 2 ###########################
    # Generating values for all the frames in the window
    fr = window["first"]
    while fr <= window["last"]:
        lottie.append({})
        lottie[-1]["i"], lottie[-1]["o"] = {}, {}
        lottie[-1]["i"]["x"] = lottie[-1]["i"]["y"] = 0.5   # Does not matter because frames are adjacent
        lottie[-1]["o"]["x"] = lottie[-1]["o"]["y"] = 0.5   # Does not matter because frames are adjacent
        lottie[-1]["t"] = fr
        lottie[-1]["s"], lottie[-1]["e"] = [], []           # Start and end value of the path
        st_val, en_val = lottie[-1]["s"], lottie[-1]["e"]
        st_val.append({})
        en_val.append({})
        st_val, en_val = st_val[0], en_val[0]
        st_val["i"], st_val["o"], st_val["v"], st_val["c"] = [], [], [], False
        en_val["i"], en_val["o"], en_val["v"], en_val["c"] = [], [], [], False
        for entry in bline_point:
            composite = entry[0]
            for child in composite:
                if child.tag == "point_path":
                    dictionary = ast.literal_eval(child.text)
                    pos_cur = get_vector_at_frame(dictionary, fr)
                    pos_next = get_vector_at_frame(dictionary, fr + 1)
                elif child.tag == "t1":
                    t1 = child[0]
                elif child.tag == "t2":
                    t2 = child[0]
                elif child.tag == "split_radius":
                    split_r = child
                elif child.tag == "split_angle":
                    split_a = child

            tangent1_cur, tangent2_cur = get_tangent_at_frame(t1, t2, split_r, split_a, fr)
            tangent1_next, tangent2_next = get_tangent_at_frame(t1, t2, split_r, split_a, fr)

            # Convert to Lottie format
            tangent1_cur /= 3
            tangent1_next /= 3
            tangent2_cur /= 3
            tangent2_next /= 3

            # Synfig and Lottie use different in tangents SEE DOCUMENTATION
            tangent1_cur *= -1
            tangent1_next *= -1

            # Important: t1 and t2 have to be relative
            # The y-axis is different in lottie
            tangent1_cur.val2 = -tangent1_cur.val2
            tangent2_cur.val2 = -tangent2_cur.val2
            tangent1_next.val2 = -tangent1_next.val2
            tangent2_next.val2 = -tangent2_next.val2

            # Store values in dictionary
            st_val["i"].append([tangent1_cur.val1, tangent1_cur.val2])
            st_val["o"].append([tangent2_cur.val1, tangent2_cur.val2])
            st_val["v"].append(pos_cur)
            en_val["i"].append([tangent1_next.val1, tangent1_next.val2])
            en_val["o"].append([tangent2_next.val1, tangent2_next.val2])
            en_val["v"].append(pos_next)
        fr += 1
    # Setting final time
    lottie.append({})
    lottie[-1]["t"] = fr

def gen_dynamic_list_shapePropKeyframe(lottie, dynamic_list):
    """
    
    """
    ################## SECTION 1 ################
    # Inserting the waypoints if not animated, finding the first and last frame
    # Calculating the path after this
    window = {}
    window["first"] = sys.maxsize
    window["last"] = -1
    count = 0

    for entry in dynamic_list:
        pos = entry
        update_frame_window(pos[0], window)

        new_pos = gen_dummy_waypoint(pos, "entry", "vector")
        pos.getparent().remove(pos)
        dynamic_list.insert(count, new_pos)

        # Generate path for lottie format
        path_dict = {}
        gen_properties_multi_dimensional_keyframed(path_dict, new_pos[0], 0)
        # Store in lxml element
        path_lxml = etree.Element("pos_path")
        path_lxml.text = str(path_dict)
        dynamic_list[count].append(path_lxml)

        if window["first"] == sys.maxsize and window["last"] == -1:
            window["first"] = window["last"] = 0
    ################ END OF SECTION 1 ##############

    ################ SECTION 2 #####################
    # Generating values for all the frames in the window
    fr = window["first"]
    while fr <= window["last"]:
        lottie.append({})
        lottie[-1]["i"], lottie[-1]["o"] = {}, {}
        lottie[-1]["i"]["x"] = lottie[-1]["i"]["y"] = 0.5   # Does not matter because frames are adjacent
        lottie[-1]["o"]["x"] = lottie[-1]["o"]["y"] = 0.5   # Does not matter because frames are adjacent
        lottie[-1]["t"] = fr
        lottie[-1]["s"], lottie[-1]["e"] = [], []           # Start and end value of the path
        st_val, en_val = lottie[-1]["s"], lottie[-1]["e"]
        st_val.append({})
        en_val.append({})
        st_val, en_val = st_val[0], en_val[0]
        st_val["i"], st_val["o"], st_val["v"], st_val["c"] = [], [], [], False
        en_val["i"], en_val["o"], en_val["v"], en_val["c"] = [], [], [], False
        for entry in dynamic_list:
            # Only two childs, one should be animated, other one is path
            for child in entry:
                if child.tag == "pos_path":
                    dictionary = ast.literal_eval(child.text)
                    pos_cur = get_vector_at_frame(dictionary, fr)
                    pos_next = get_vector_at_frame(dictionary, fr + 1)

            tangent1_cur, tangent2_cur = Vector(0, 0), Vector(0, 0)
            tangent1_next, tangent2_next = Vector(0, 0), Vector(0, 0)

            # Store values in dictionary
            st_val["i"].append([tangent1_cur.val1, tangent1_cur.val2])
            st_val["o"].append([tangent2_cur.val1, tangent2_cur.val2])
            st_val["v"].append(pos_cur)
            en_val["i"].append([tangent1_next.val1, tangent1_next.val2])
            en_val["o"].append([tangent2_next.val1, tangent2_next.val2])
            en_val["v"].append(pos_next)
        fr += 1
    # Setting the final time
    lottie.append({})
    lottie[-1]["t"] = fr
