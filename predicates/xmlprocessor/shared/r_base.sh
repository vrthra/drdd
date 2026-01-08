#!/bin/bash

SCRIPT_DIR=$1
LIB_DIR="${SCRIPT_DIR}/../lib"

HOST=127.0.0.1
BASEX_GOOD_PORT=$2
BASEX_BAD_PORT=$((BASEX_GOOD_PORT + 1))

INPUT_NAME=${3:-input.xml}

# ensure servers are reachable on the given ports
check_listening() {
	local host="$1" port="$2"
	
	# check with netcat
	nc -z "$host" "$port" >/dev/null 2>&1
}

target_saxon="saxon"
target_basex_bad="basex_bad"
target_basex_good="basex_good"

cleanup() {
	local ec=$?

	rm -f \
		"${SCRIPT_DIR}/${target_saxon}_raw_result.xml" \
		"${SCRIPT_DIR}/${target_saxon}_processed_result.txt" \
		"${SCRIPT_DIR}/${target_basex_bad}_raw_result.xml" \
		"${SCRIPT_DIR}/${target_basex_bad}_processed_result.txt" \
		"${SCRIPT_DIR}/${target_basex_good}_raw_result.xml" \
		"${SCRIPT_DIR}/${target_basex_good}_processed_result.txt"

	exit "$ec"
}

trap cleanup EXIT

# run saxon
java -cp "${LIB_DIR}/saxon-he-12.4.jar:${LIB_DIR}/xmlresolver-5.2.0/lib/*" net.sf.saxon.Query -s:"$SCRIPT_DIR/$INPUT_NAME" -q:"$SCRIPT_DIR/query.xq" > ${target_saxon}_raw_result.xml 2>&1
ret=$?
	
if [ $ret != 0 ]; then
	exit 1
fi

# run basex_bad
java -cp "${LIB_DIR}/basex-${BAD_VERSION}.jar" org.basex.BaseXClient -n "$HOST" -p "$BASEX_BAD_PORT" -U admin -P password -i "$SCRIPT_DIR/$INPUT_NAME" "$SCRIPT_DIR/query.xq" > ${target_basex_bad}_raw_result.xml 2>&1
ret=$?

if [ $ret != 0 ]; then
	if ! check_listening "$HOST" "$BASEX_BAD_PORT"; then
		echo "Error: BaseX bad server not reachable on $HOST:$BASEX_BAD_PORT" >&2
		exit 3
	elif [[ ! -f "${LIB_DIR}/basex-${BAD_VERSION}.jar" ]]; then
		echo "Error: BaseX .jar file not found: ${LIB_DIR}/basex-${BAD_VERSION}.jar" >&2
		exit 4
	fi

	exit 1
fi

# run basex_good
java -cp "${LIB_DIR}/basex-${GOOD_VERSION}.jar" org.basex.BaseXClient -n "$HOST" -p "$BASEX_GOOD_PORT" -U admin -P password -i "$SCRIPT_DIR/$INPUT_NAME" "$SCRIPT_DIR/query.xq" > ${target_basex_good}_raw_result.xml 2>&1
ret=$?

if [ $ret != 0 ]; then
	if ! check_listening "$HOST" "$BASEX_GOOD_PORT"; then
		echo "Error: BaseX good server not reachable on $HOST:$BASEX_GOOD_PORT" >&2
		exit 3
	elif [[ ! -f "${LIB_DIR}/basex-${GOOD_VERSION}.jar" ]]; then
		echo "Error: BaseX .jar file not found: ${LIB_DIR}/basex-${GOOD_VERSION}.jar" >&2
		exit 4
	fi

	exit 1
fi

# process saxon result
grep -o 'id="[^"]*"' ${target_saxon}_raw_result.xml | sed 's/id="//g' | sed 's/"//g' | grep -v '^[[:space:]]*$' > ${target_saxon}_processed_result.txt

# process basex_bad result
grep -o 'id="[^"]*"' ${target_basex_bad}_raw_result.xml | sed 's/id="//g' | sed 's/"//g' | grep -v '^[[:space:]]*$' > ${target_basex_bad}_processed_result.txt

# process basex_good result
grep -o 'id="[^"]*"' ${target_basex_good}_raw_result.xml | sed 's/id="//g' | sed 's/"//g' | grep -v '^[[:space:]]*$' > ${target_basex_good}_processed_result.txt

# diff, files should be different
if diff ${target_saxon}_processed_result.txt ${target_basex_bad}_processed_result.txt > /dev/null 2>&1; then
	exit 1
fi

# diff, files should be same
if ! diff ${target_saxon}_processed_result.txt ${target_basex_good}_processed_result.txt > /dev/null 2>&1; then
	exit 1
fi

exit 0
