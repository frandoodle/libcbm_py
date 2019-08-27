import pandas as pd
import numpy as np

from libcbm.input.sit import sit_format


def unpack_column(table, column_description):
    data = table.iloc[:, column_description["index"]]
    if "type" in column_description:
        data = data.astype(column_description["type"])
    if "min_value" in column_description:
        if len(data[data > column_description["min_value"]]):
            raise ValueError("")
    return data


def unpack_table(table, column_descriptions):
    cols = [x["name"] for x in column_descriptions]
    data = {
        x["name"]: unpack_column(table, x)
        for x in column_descriptions}
    return pd.DataFrame(columns=cols, data=data)


def parse_age_classes(age_class_table):
    return unpack_table(
        age_class_table, sit_format.get_age_class_format())


def parse_disturbance_types(disturbance_types_table):
    return unpack_table(
        disturbance_types_table,
        sit_format.get_disturbance_type_format(
            len(disturbance_types_table.columns)))


def parse_classifiers(classifiers_table):

    classifier_keyword = "_CLASSIFIER"
    classifiers_format = sit_format.get_classifier_format(
        len(classifiers_table.columns))
    unpacked = unpack_table(
        classifiers_table, classifiers_format
    )
    classifiers = unpacked \
        .loc[unpacked["name"] == classifier_keyword]
    classifiers = pd.DataFrame(
        data={
            "id": classifiers.id,
            # for classifiers, the 3rd column is used for the name
            "name": classifiers.description},
        columns=["id", "name"])

    # filter out rows that have the _classifier keyword and also
    # any rows that have a value on the 3rd or greater column.
    # This is the set of classifier values.
    classifier_values = unpacked \
        .loc[pd.isnull(unpacked.iloc[:, 3:]).all(axis=1) &
             (unpacked["name"] != classifier_keyword)]

    classifier_values = pd.DataFrame({
        "classifier_id": classifier_values.id,
        "name": classifier_values.name,
        "description": classifier_values.description
    })

    aggregate_values = []
    classifier_aggregates = unpacked.loc[
        ~pd.isnull(unpacked.iloc[:, 3:]).all(axis=1)]
    for i in range(0, classifier_aggregates.shape[0]):

        agg_values = classifier_aggregates.iloc[i, 3:]
        agg_values = agg_values[~pd.isnull(agg_values)]
        aggregate_values.append({
            "classifier_id": classifier_aggregates.iloc[i, :]["id"],
            "name": classifier_aggregates.iloc[i, :]["name"],
            "description": classifier_aggregates.iloc[i, :]["description"],
            "classifier_values": list(agg_values[:])
        })


def parse_inventory(inventory_table, classifiers, classifier_values):
    inventory = unpack_table(
        inventory_table,
        sit_format.get_inventory_format(
            classifiers.name,
            len(inventory_table.columns)))

    # validate the classifier values in the inventory table
    for row in classifiers.itertuples():
        a = inventory[row.name].unique()
        b = classifier_values[
            classifier_values["classifier_id"] == row.id]["name"].unique()
        diff = np.setdiff1d(a, b)
        if len(diff) > 0:
            raise ValueError(
                "Undefined classifier values detected: "
                f"classifier: '{row.name}', values: {diff}")

    return inventory
